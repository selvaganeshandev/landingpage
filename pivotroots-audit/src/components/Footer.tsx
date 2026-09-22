import { Logo } from "./Nav";
import { PRIVACY_URL, SHOW_POWERED_BY, TERMS_URL } from "@/lib/site";

export function Footer() {
  return (
    <footer>
      <div className="wrap">
        <div className="cols">
          <div>
            <Logo height={24} />
            <p>Award-winning digital marketing agency in India &amp; UAE. SEO, performance, media, UX, analytics, creative — and now, AI visibility.</p>
            {SHOW_POWERED_BY && <p className="powered">Audit engine powered by PromptMaxx</p>}
          </div>
          <div><h4>Mumbai</h4>Trade Star, Office 3, 2nd Floor, A wing, JB Nagar, Andheri Kurla Road, 400059</div>
          <div><h4>Bangalore</h4>Divyasree Technopolis 124-125, Yemalur Main Rd, 560037</div>
          <div><h4>Gurgaon</h4>6th Floor, Tower C, Building 8, DLF Cyber City, Phase II, 122002</div>
          <div>
            <h4>Dubai</h4>601 Tiffany Towers, Cluster W, JLT
            <h4 className="gap">Enquiries</h4>hello@pivotroots.com<br />+91 99202 98092
          </div>
        </div>
        <div className="bottom">
          <span>© {new Date().getFullYear()} PivotRoots Digital Pvt. Ltd.</span>
          <span><a href={PRIVACY_URL}>Privacy</a> · <a href={TERMS_URL}>Terms</a></span>
        </div>
      </div>
    </footer>
  );
}
