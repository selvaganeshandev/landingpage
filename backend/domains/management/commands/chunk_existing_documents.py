"""
Management command to create chunks for existing reference documents.
Run this once after deploying the chunking feature to backfill chunks
for documents that were uploaded before this feature existed.

Usage: python manage.py chunk_existing_documents
"""

from django.core.management.base import BaseCommand
from domains.models import ReferenceDocument, ReferenceDocumentChunk


class Command(BaseCommand):
    help = 'Create chunks for existing reference documents that do not have chunks yet'

    def handle(self, *args, **options):
        docs = ReferenceDocument.objects.filter(
            extracted_text__isnull=False,
        ).exclude(extracted_text='')

        total = docs.count()
        self.stdout.write(f"Found {total} documents with extracted text")

        created_count = 0
        skipped_count = 0

        for doc in docs:
            # Skip if already chunked
            if doc.chunks.exists():
                skipped_count += 1
                continue

            text = doc.extracted_text
            chunk_size = ReferenceDocumentChunk.CHUNK_SIZE
            overlap = ReferenceDocumentChunk.CHUNK_OVERLAP
            chunks = []
            start = 0
            chunk_index = 0

            while start < len(text):
                end = start + chunk_size
                chunk_text = text[start:end]

                if chunk_text.strip():
                    chunks.append(ReferenceDocumentChunk(
                        document=doc,
                        chunk_index=chunk_index,
                        chunk_text=chunk_text
                    ))
                    chunk_index += 1

                start += chunk_size - overlap

            if chunks:
                ReferenceDocumentChunk.objects.bulk_create(chunks)

            created_count += 1
            self.stdout.write(
                f"  [{created_count}/{total}] {doc.file_name}: "
                f"{len(text)} chars -> {len(chunks)} chunks"
            )

        self.stdout.write(self.style.SUCCESS(
            f"\nDone! Chunked: {created_count}, Skipped (already chunked): {skipped_count}"
        ))
