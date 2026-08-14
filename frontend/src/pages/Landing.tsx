import { useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';

export function Landing() {
  const observerRef = useRef<IntersectionObserver | null>(null);

  useEffect(() => {
    observerRef.current = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            (entry.target as HTMLElement).style.opacity = '1';
            (entry.target as HTMLElement).style.transform = 'translateY(0)';
          }
        });
      },
      { threshold: 0.1 }
    );

    const elements = document.querySelectorAll('.animate-on-scroll');
    elements.forEach((el) => {
      (el as HTMLElement).style.opacity = '0';
      (el as HTMLElement).style.transform = 'translateY(20px)';
      (el as HTMLElement).style.transition = 'all 0.8s cubic-bezier(0.16, 1, 0.3, 1)';
      observerRef.current?.observe(el);
    });

    return () => {
      observerRef.current?.disconnect();
    };
  }, []);

  return (
    <div className="bg-background font-body-md text-on-surface">
      <header className="fixed top-0 left-0 right-0 h-24 backdrop-blur-xl z-40 flex items-center justify-between px-8 md:px-16 lg:px-24 bg-surface/80 border-b border-surface-container/50 shadow-sm">
        <div className="flex items-center gap-3">
          <img src="/logo.png" alt="LogiSight" className="h-8 w-auto object-contain" onError={(e) => { e.currentTarget.style.display = 'none'; }} />
          <span className="font-headline-md-mobile text-[24px] font-bold tracking-tighter text-on-surface">
            LogiSight
          </span>
        </div>
        <div className="flex items-center gap-4">
          <Link
            to="/login"
            className="px-6 py-2.5 rounded-full font-label-sm text-label-sm border border-outline-variant text-on-surface hover:bg-surface-container transition-all"
          >
            Login
          </Link>
          <Link
            to="/login"
            className="bg-apple-blue hover:bg-[#005bb5] text-white px-6 py-2.5 rounded-full font-label-sm text-label-sm transition-all shadow-sm hover:shadow-md"
          >
            Get a Demo
          </Link>
        </div>
      </header>
      
      <main className="relative pt-24 min-h-screen bg-background flex flex-col">
        <div className="flex flex-col w-full bg-background flex-1 font-body-md text-on-surface">
          <section className="relative min-h-[calc(100vh-6rem)] flex items-center justify-center pt-8 pb-spacing-section-gap-lg px-8 md:px-16 lg:px-24 overflow-hidden">
            <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden">
              <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)]"></div>
              <div className="absolute top-[-20%] right-[-10%] w-[50vw] h-[50vw] rounded-full bg-primary/20 blur-[120px]"></div>
              <div className="absolute bottom-[10%] left-[-10%] w-[40vw] h-[40vw] rounded-full bg-apple-blue/20 blur-[120px]"></div>
              <div className="absolute top-[20%] left-[20%] w-[30vw] h-[30vw] rounded-full bg-tertiary/15 blur-[100px]"></div>
            </div>
            <div className="relative z-10 w-full max-w-6xl mx-auto flex flex-col items-center text-center animate-on-scroll">
              <h1 className="font-display-lg text-display-lg text-on-surface mb-6 max-w-4xl mx-auto mt-8">
                Freight Audit Intelligence for the Modern Forwarder.
              </h1>
              <p className="font-body-lg text-body-lg text-on-surface-variant max-w-2xl mx-auto mb-10">
                Automate complex invoice reconciliation, uncover hidden overcharges, and streamline your entire logistics financial workflow with unprecedented accuracy.
              </p>
              <div className="flex items-center gap-4">
                <Link
                  to="/login"
                  className="bg-apple-blue hover:bg-[#005bb5] text-white px-8 py-4 rounded-full font-label-sm text-label-sm transition-all shadow-md hover:shadow-lg transform hover:-translate-y-0.5"
                >
                  Start Free Trial
                </Link>
                <button className="bg-surface-container-lowest text-on-surface px-8 py-4 rounded-full font-label-sm text-label-sm transition-all hover:bg-surface-container shadow-sm flex items-center gap-2 border border-surface-container">
                  <span className="material-symbols-outlined text-[20px]">mail</span>
                  Contact Sales
                </button>
              </div>
            </div>
          </section>

          <section className="min-h-screen flex items-center justify-center py-16 px-8 md:px-16 lg:px-24 bg-surface-container-lowest relative z-20">
            <div className="max-w-7xl mx-auto animate-on-scroll">
              <div className="flex flex-col items-center mb-16 text-center">
                <h2 className="font-headline-md text-headline-md text-on-surface mb-6">Intelligence at every step.</h2>
                <p className="font-body-lg text-body-lg text-on-surface-variant max-w-3xl">Our proprietary OCR and machine learning engines parse unstructured freight data into actionable financial truth.</p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <div className="group relative bg-surface p-8 rounded-[32px] shadow-sm hover:shadow-md transition-all duration-500 overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-br from-surface-container-lowest/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                  <div className="w-14 h-14 bg-apple-blue/10 rounded-2xl flex items-center justify-center mb-8">
                    <span className="material-symbols-outlined text-apple-blue text-3xl">document_scanner</span>
                  </div>
                  <h3 className="font-headline-md-mobile text-headline-md-mobile text-on-surface mb-4">Extract</h3>
                  <p className="font-body-md text-body-md text-on-surface-variant">Ingest PDFs, EDI, and email attachments automatically. High-fidelity OCR captures line-item details with 99.8% accuracy.</p>
                </div>
                <div className="group relative bg-surface p-8 rounded-[32px] shadow-sm hover:shadow-md transition-all duration-500 overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-br from-surface-container-lowest/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                  <div className="w-14 h-14 bg-surface-container-high rounded-2xl flex items-center justify-center mb-8">
                    <span className="material-symbols-outlined text-on-surface text-3xl">analytics</span>
                  </div>
                  <h3 className="font-headline-md-mobile text-headline-md-mobile text-on-surface mb-4">Analyze</h3>
                  <p className="font-body-md text-body-md text-on-surface-variant">Structure disparate data formats into a unified taxonomy. Normalize carrier codes and accessorial charges instantly.</p>
                </div>
                <div className="group relative bg-surface p-8 rounded-[32px] shadow-sm hover:shadow-md transition-all duration-500 overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-br from-surface-container-lowest/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                  <div className="w-14 h-14 bg-surface-container-high rounded-2xl flex items-center justify-center mb-8">
                    <span className="material-symbols-outlined text-on-surface text-3xl">fact_check</span>
                  </div>
                  <h3 className="font-headline-md-mobile text-headline-md-mobile text-on-surface mb-4">Audit</h3>
                  <p className="font-body-md text-body-md text-on-surface-variant">Cross-reference billed amounts against negotiated contracted rates, highlighting discrepancies down to the penny.</p>
                </div>
                <div className="group relative bg-surface p-8 rounded-[32px] shadow-sm hover:shadow-md transition-all duration-500 overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-br from-surface-container-lowest/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                  <div className="w-14 h-14 bg-surface-container-high rounded-2xl flex items-center justify-center mb-8">
                    <span className="material-symbols-outlined text-on-surface text-3xl">handshake</span>
                  </div>
                  <h3 className="font-headline-md-mobile text-headline-md-mobile text-on-surface mb-4">Resolve</h3>
                  <p className="font-body-md text-body-md text-on-surface-variant">Generate automated dispute workflows. Collaborate with carriers directly within the platform to resolve claims faster.</p>
                </div>
              </div>
            </div>
          </section>

          <section className="min-h-screen flex items-center justify-center py-16 px-8 md:px-16 lg:px-24 bg-surface relative overflow-hidden">
            <div className="w-full max-w-7xl mx-auto flex flex-col lg:flex-row items-center justify-between gap-16 animate-on-scroll">
              <div className="w-full lg:w-1/2 flex flex-col items-start z-10">
                <h2 className="font-headline-md text-headline-md text-on-surface mb-8">Uncover hidden margin leakages.</h2>
                <p className="font-body-lg text-body-lg text-on-surface-variant mb-10">
                  Our dashboard provides granular visibility into your freight spend. Identify which carriers consistently overcharge, which lanes are least profitable, and optimize your supply chain network accordingly.
                </p>
                <ul className="space-y-6 w-full mb-12">
                  <li className="flex items-start gap-4">
                    <span className="material-symbols-outlined text-apple-blue mt-1">check_circle</span>
                    <div>
                      <h4 className="font-label-sm text-label-sm text-on-surface mb-1">Contract Compliance</h4>
                      <p className="font-body-md text-body-md text-on-surface-variant text-sm">Ensure every invoice matches your complex routing guides.</p>
                    </div>
                  </li>
                  <li className="flex items-start gap-4">
                    <span className="material-symbols-outlined text-apple-blue mt-1">check_circle</span>
                    <div>
                      <h4 className="font-label-sm text-label-sm text-on-surface mb-1">Accessorial Analysis</h4>
                      <p className="font-body-md text-body-md text-on-surface-variant text-sm">Spot trends in detention, demurrage, and unexpected fees.</p>
                    </div>
                  </li>
                </ul>
              </div>
              <div className="w-full lg:w-1/2 relative h-[500px] rounded-[40px] overflow-hidden shadow-2xl bg-surface-container-lowest">
                <div 
                  className="absolute inset-0 bg-cover bg-center opacity-80 mix-blend-luminosity" 
                  style={{ backgroundImage: "url('https://images.unsplash.com/photo-1551288049-bebda4e38f71?q=80&w=2070&auto=format&fit=crop')" }}
                ></div>
                <div className="absolute bottom-8 left-8 right-8 p-6 bg-surface-container-lowest/80 backdrop-blur-xl rounded-2xl shadow-lg border-t border-surface-container-high/50 flex items-center justify-between">
                  <div>
                    <p className="font-label-sm text-label-sm text-on-surface-variant mb-1 uppercase tracking-wider">Total Recovered YTD</p>
                    <p className="font-headline-md-mobile text-headline-md-mobile text-on-surface">$1.24M</p>
                  </div>
                  <div className="w-16 h-16 bg-apple-blue/10 rounded-full flex items-center justify-center">
                    <span className="material-symbols-outlined text-apple-blue text-3xl">trending_up</span>
                  </div>
                </div>
              </div>
            </div>
          </section>

          {/* Footer added */}
          <footer className="mt-auto py-12 border-t border-surface-container-high bg-surface-container-lowest px-spacing-margin-desktop">
             <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
                <div className="flex items-center gap-2">
                   <img src="/logo.png" alt="LogiSight" className="h-6 w-auto object-contain" onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                   <span className="font-label-sm text-label-sm font-semibold text-on-surface">LogiSight</span>
                </div>
                <div className="text-on-surface-variant font-label-sm text-[13px]">
                   &copy; {new Date().getFullYear()} LogiSight. All rights reserved.
                </div>
                <div className="flex gap-6 font-label-sm text-[13px] text-on-surface-variant">
                   <a href="#" className="hover:text-primary transition-colors">Privacy Policy</a>
                   <a href="#" className="hover:text-primary transition-colors">Terms of Service</a>
                </div>
             </div>
          </footer>
        </div>
      </main>
    </div>
  );
}
