"""Tests for brand recognition in AI answers.

The bug these exist to prevent: domain 40 ('CanaraHSBCLife Insurance',
canarahsbclife.com) recorded 972 completed rows and ZERO mentions, while 87 of
those rows contained the brand in the response text. Every identity pattern was
derived from the display name treated as a hostname, so nothing the model
actually wrote could match.

Two things are being asserted here, and the second matters as much as the first:

  1. the brand that used to be invisible is now found, in each of the spellings
     an LLM produces
  2. the brands that already worked are matched EXACTLY as before — no new
     false positives, no inflated counts

Run:  python tests/standalone/engine/core/test_brand_identity.py
"""
import importlib.util
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = REPOSITORY_ROOT / 'engine' / 'core' / 'brand_identity.py'

_spec = importlib.util.spec_from_file_location('brand_identity_under_test', MODULE_PATH)
brand_identity = importlib.util.module_from_spec(_spec)
sys.modules['brand_identity_under_test'] = brand_identity
_spec.loader.exec_module(brand_identity)

build_brand_identity = brand_identity.build_brand_identity
tokenise = brand_identity.tokenise
host_from_value = brand_identity.host_from_value


CANARA_URL = 'https://www.canarahsbclife.com'
CANARA_NAME = 'CanaraHSBCLife Insurance'


def test_camel_case_names_split_into_words():
    print("  a name written without spaces still yields its words")
    assert tokenise(CANARA_NAME) == ['canara', 'hsbc', 'life', 'insurance']
    assert tokenise('Grown Brilliance') == ['grown', 'brilliance']
    assert tokenise('Zerodha') == ['zerodha']
    assert tokenise('AppKodes') == ['app', 'kodes']
    assert tokenise('IBM') == ['ibm']
    assert tokenise('') == []


def test_a_display_name_is_not_a_hostname():
    print("  a name with a space is rejected as a host instead of becoming one")
    assert host_from_value(CANARA_NAME) == ''
    assert host_from_value('https://www.canarahsbclife.com') == 'canarahsbclife.com'
    assert host_from_value('zerodha.com') == 'zerodha.com'
    assert host_from_value('') == ''


def test_canarahsbc_is_found_however_the_model_writes_it():
    print("  the regression case: every real spelling counts as a mention")
    identity = build_brand_identity(CANARA_URL, CANARA_NAME)
    for answer in (
        'Canara HSBC Life Insurance offers a term plan.',
        'Consider CanaraHSBCLife Insurance for coverage.',
        'canara hsbc life is among the insurers listed.',
        'See Canara-HSBC-Life-Insurance for details.',
        'Visit canarahsbclife.com to compare plans.',
    ):
        assert identity.mention_count(answer) >= 1, f'missed: {answer}'
        assert identity.appears_in(answer), f'missed: {answer}'


def test_canarahsbc_citations_resolve():
    print("  the same brand's URLs are recognised as its own citations")
    identity = build_brand_identity(CANARA_URL, CANARA_NAME)
    text = (
        'Sources: https://www.canarahsbclife.com/term-insurance and '
        'https://canarahsbclife.com/faq plus https://policybazaar.com/x'
    )
    urls = identity.citation_urls(text)
    assert len(urls) == 2, urls
    assert all('canarahsbclife' in url for url in urls), urls
    assert not any('policybazaar' in url for url in urls), urls


def test_unrelated_brands_are_not_matched():
    print("  a different insurer in the same answer is not counted")
    identity = build_brand_identity(CANARA_URL, CANARA_NAME)
    for answer in (
        'HDFC Life Insurance and ICICI Prudential lead the segment.',
        'Life insurance in India is competitive.',
        'Canara Bank is a separate public sector lender.',
    ):
        assert identity.mention_count(answer) == 0, f'false positive: {answer}'


def test_brands_that_already_worked_are_unchanged():
    print("  domains whose name already equalled their URL behave as before")
    zerodha = build_brand_identity('https://zerodha.com', 'Zerodha')
    assert zerodha.mention_count('Zerodha is the largest broker.') == 1
    assert zerodha.mention_count('Use zerodha.com to open an account.') == 1
    assert zerodha.mention_count('Groww and Upstox are alternatives.') == 0

    grown = build_brand_identity('https://grownbrilliance.com', 'Grown Brilliance')
    assert grown.mention_count('Grown Brilliance sells lab diamonds.') == 1
    assert grown.mention_count('grownbrilliance is worth a look.') == 1
    assert grown.mention_count('Brilliant Earth is the competitor.') == 0


def test_one_mention_is_never_counted_twice():
    print("  overlapping patterns collapse to a single mention")
    identity = build_brand_identity(CANARA_URL, CANARA_NAME)
    # 'canarahsbclife.com' matches the host pattern AND the word pattern.
    assert identity.mention_count('Go to canarahsbclife.com now.') == 1
    # Two genuinely separate namings stay two.
    assert identity.mention_count(
        'Canara HSBC Life Insurance is one. Canara HSBC Life is the same firm.'
    ) == 2


def test_words_are_not_joined_across_a_sentence_boundary():
    print("  a bounded separator stops unrelated words merging into a mention")
    identity = build_brand_identity(CANARA_URL, CANARA_NAME)
    text = 'The bank is Canara.                     HSBC Life is unrelated here.'
    assert identity.mention_count(text) == 0, 'separator run should not bridge'


def test_a_legacy_caller_passing_only_a_name_still_works():
    print("  the old single-argument call site degrades, it does not crash")
    identity = build_brand_identity(CANARA_NAME)
    assert identity.is_resolvable
    assert identity.mention_count('CanaraHSBCLife Insurance is listed.') == 1
    # Without the URL there is no host, so no citation can be attributed.
    assert identity.citation_urls('https://canarahsbclife.com/x') == []


def test_a_url_unrelated_to_the_name_keeps_both_identities():
    print("  when the URL is not spelled by the name, both are still matched")
    identity = build_brand_identity('https://kite.trade', 'Zerodha Kite')
    assert identity.mention_count('Zerodha Kite is the trading app.') == 1
    assert identity.mention_count('kite.trade hosts the platform.') >= 1


def test_a_second_level_registry_is_not_mistaken_for_the_brand():
    print("  iob.bank.in is IOB, not every answer containing the word 'bank'")
    for url, name in (
        ('https://iob.bank.in', 'IOB Bank'),
        ('https://kotak811.bank.in', 'Kotak811'),
        ('https://hsbc.bank.in', 'HSBC Bank'),
    ):
        identity = build_brand_identity(url, name)
        assert identity.label != 'bank', f'{url} collapsed to the registry label'
        assert identity.mention_count(
            'Every bank in India offers a savings account.'
        ) == 0, f'{url} matched a generic sentence about banks'

    iob = build_brand_identity('https://iob.bank.in', 'IOB Bank')
    assert iob.mention_count('IOB Bank raised its FD rates.') >= 1
    kotak = build_brand_identity('https://kotak811.bank.in', 'Kotak811')
    assert kotak.mention_count('Kotak 811 is a zero-balance account.') >= 1


def test_a_label_that_abbreviates_the_name_still_segments():
    print("  merillife.com is matched as 'Meril Life', not only as one blob")
    identity = build_brand_identity('https://merillife.com', 'Meril Lifesciences')
    assert identity.mention_count('Meril Lifesciences makes stents.') >= 1
    assert identity.mention_count('Meril Life is the consumer brand.') >= 1
    assert identity.mention_count('merillife.com lists the catalogue.') >= 1
    assert identity.mention_count('Life sciences is a broad sector.') == 0


def test_punctuation_in_a_label_does_not_block_segmentation():
    print("  paradise-kerala.com segments the same as paradisekerala.com")
    identity = build_brand_identity('https://paradise-kerala.com', 'Paradise Kerala')
    assert identity.mention_count('Paradise Kerala runs the tour.') >= 1
    assert identity.mention_count('paradise-kerala.com has the itinerary.') >= 1


def test_short_brands_do_not_match_everything():
    print("  patterns below the minimum length are dropped, as before")
    identity = build_brand_identity('', 'Ab')
    assert not identity.is_resolvable
    assert identity.mention_count('Ab is everywhere in absolutely any text.') == 0


def main():
    print("=" * 78)
    print("BRAND IDENTITY MATCHING")
    print("=" * 78)
    for test in (
        test_camel_case_names_split_into_words,
        test_a_display_name_is_not_a_hostname,
        test_canarahsbc_is_found_however_the_model_writes_it,
        test_canarahsbc_citations_resolve,
        test_unrelated_brands_are_not_matched,
        test_brands_that_already_worked_are_unchanged,
        test_one_mention_is_never_counted_twice,
        test_words_are_not_joined_across_a_sentence_boundary,
        test_a_legacy_caller_passing_only_a_name_still_works,
        test_a_url_unrelated_to_the_name_keeps_both_identities,
        test_a_second_level_registry_is_not_mistaken_for_the_brand,
        test_a_label_that_abbreviates_the_name_still_segments,
        test_punctuation_in_a_label_does_not_block_segmentation,
        test_short_brands_do_not_match_everything,
    ):
        test()
    print("=" * 78)
    print("ALL TESTS PASSED")


if __name__ == '__main__':
    main()
