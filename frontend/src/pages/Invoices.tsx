import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getInvoices, getQuotes, uploadInvoice } from '../api/client';
import { useAuth } from '../hooks/useAuth';

export function Invoices() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const qc = useQueryClient();
  const isForwarder = user?.role === 'forwarder';
  const isClient = user?.role === 'client';

  const [showUpload, setShowUpload] = useState(false);
  const [selectedQuoteId, setSelectedQuoteId] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const { data: invoices = [], isLoading } = useQuery({
    queryKey: ['invoices'],
    queryFn: () => getInvoices(),
  });

  const { data: quotes = [] } = useQuery({
    queryKey: ['quotes'],
    queryFn: getQuotes,
    enabled: isForwarder,
  });

  const acceptedQuotes = quotes.filter((q) => q.status === 'ACCEPTED');

  const uploadMutation = useMutation({
    mutationFn: () => uploadInvoice(selectedQuoteId!, selectedFile!),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['invoices'] });
      setShowUpload(false);
      setSelectedQuoteId('');
      setSelectedFile(null);
      setUploadError(null);
      navigate(`/app/invoices/${data.id}`);
    },
    onError: (err: Error) => setUploadError(err.message),
  });

  const handleUpload = () => {
    if (!selectedQuoteId) { setUploadError('Select a quote'); return; }
    if (!selectedFile) { setUploadError('Select a PDF file'); return; }
    setUploadError(null);
    uploadMutation.mutate();
  };

  return (
    <div className="flex flex-col w-full relative">
      <div className="px-spacing-margin-desktop py-spacing-margin-desktop mb-spacing-section-gap-sm">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 mb-10">
          <div>
            <p className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-widest mb-2">Documents</p>
            <h1 className="font-display-lg text-display-lg text-on-surface tracking-tighter leading-none">Invoices</h1>
            <p className="text-on-surface-variant mt-2 text-body-md max-w-xl">
              {isClient ? 'Review and analyse uploaded freight invoices.' : 'Upload invoice PDFs against accepted quotes.'}
            </p>
          </div>
          {isForwarder && (
            <button
              onClick={() => setShowUpload(true)}
              className="flex items-center gap-2 bg-primary text-on-primary px-6 py-3 rounded-full font-label-sm text-label-sm transition-all shadow-sm hover:shadow-md transform active:scale-95"
            >
              <span className="material-symbols-outlined text-[18px]">upload</span> Upload Invoice
            </button>
          )}
        </div>

        {showUpload && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-surface-container-highest/60 backdrop-blur-sm">
            <div className="w-full max-w-md rounded-3xl border border-outline-variant bg-surface-container-lowest shadow-[0_20px_60px_-15px_rgba(0,0,0,0.1)] overflow-hidden">
              <div className="flex items-center justify-between p-6 border-b border-surface-container">
                <h2 className="font-headline-md-mobile text-headline-md-mobile text-on-surface text-[24px]">Upload Invoice</h2>
                <button
                  onClick={() => { setShowUpload(false); setSelectedFile(null); setSelectedQuoteId(''); setUploadError(null); }}
                  className="text-on-surface-variant hover:text-primary transition-colors"
                >
                  <span className="material-symbols-outlined text-[24px]">close</span>
                </button>
              </div>
              <div className="p-6 space-y-6">
                {uploadError && (
                  <div className="flex items-start gap-2 p-4 rounded-xl bg-error-container text-on-error-container border border-error/20">
                    <span className="material-symbols-outlined text-[20px] text-error flex-shrink-0">error</span>
                    <p className="text-body-md text-error">{uploadError}</p>
                  </div>
                )}
                <div>
                  <label className="block text-body-md font-medium text-on-surface mb-2">Accepted Quote</label>
                  <div className="relative">
                    <select
                      value={selectedQuoteId}
                      onChange={(e) => setSelectedQuoteId(e.target.value)}
                      className="w-full appearance-none bg-surface border border-outline-variant rounded-xl px-4 py-3 text-body-md text-on-surface focus:outline-none focus:border-primary transition-colors"
                    >
                      <option value="">Select an accepted quote…</option>
                      {acceptedQuotes.map((q) => (
                        <option key={q.id} value={q.id}>
                          {q.quote_ref} — AWB {q.tracking_number}
                        </option>
                      ))}
                    </select>
                    <span className="material-symbols-outlined absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-on-surface-variant">expand_more</span>
                  </div>
                </div>
                <div>
                  <label className="block text-body-md font-medium text-on-surface mb-2">Invoice PDF</label>
                  <div
                    onClick={() => fileRef.current?.click()}
                    className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-colors ${
                      selectedFile
                        ? 'border-apple-blue bg-apple-blue/5'
                        : 'border-outline-variant hover:border-outline hover:bg-surface-container-low'
                    }`}
                  >
                    <input
                      ref={fileRef}
                      type="file"
                      accept=".pdf"
                      className="hidden"
                      onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)}
                    />
                    <span className={`material-symbols-outlined text-[32px] mx-auto mb-3 ${selectedFile ? 'text-apple-blue' : 'text-on-surface-variant'}`}>
                      {selectedFile ? 'task' : 'upload_file'}
                    </span>
                    {selectedFile ? (
                      <p className="text-body-md text-apple-blue font-medium">{selectedFile.name}</p>
                    ) : (
                      <>
                        <p className="text-body-md text-on-surface">Click to select PDF</p>
                        <p className="text-label-sm text-on-surface-variant mt-1">Supports digital and scanned PDFs</p>
                      </>
                    )}
                  </div>
                </div>
                <div className="flex gap-4 pt-2">
                  <button
                    onClick={() => { setShowUpload(false); setSelectedFile(null); setSelectedQuoteId(''); setUploadError(null); }}
                    className="flex-1 py-3 rounded-full border border-outline-variant text-on-surface font-label-sm text-label-sm hover:bg-surface-container transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleUpload}
                    disabled={uploadMutation.isPending}
                    className="flex-1 py-3 rounded-full bg-apple-blue hover:bg-[#005bb5] disabled:opacity-60 text-white font-label-sm text-label-sm shadow-sm transition-colors flex items-center justify-center gap-2"
                  >
                    {uploadMutation.isPending ? (
                      <>
                        <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        Uploading…
                      </>
                    ) : (
                      'Upload & Extract'
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="bg-surface-container-lowest rounded-3xl p-8 shadow-sm">
          <div className="flex justify-between items-center mb-8">
            <div>
              <h3 className="font-headline-md-mobile text-headline-md-mobile text-on-surface tracking-tight">Invoice Documents</h3>
              <p className="font-body-md text-body-md text-on-surface-variant mt-1">All processed invoices and extraction results.</p>
            </div>
          </div>
          
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-16 rounded-xl border border-surface-container-highest bg-surface-container-highest/40 animate-pulse" />
              ))}
            </div>
          ) : invoices.length === 0 ? (
            <div className="py-24 text-center">
              <span className="material-symbols-outlined text-[48px] text-outline-variant mx-auto mb-4">description</span>
              <p className="text-on-surface-variant font-body-md mb-6">No invoices yet</p>
              {isForwarder && (
                <button
                  onClick={() => setShowUpload(true)}
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-apple-blue hover:bg-[#005bb5] text-white font-label-sm text-label-sm shadow-sm transition-colors"
                >
                  <span className="material-symbols-outlined text-[18px]">upload</span> Upload first invoice
                </button>
              )}
            </div>
          ) : (
            <div className="w-full overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-surface-container-highest">
                    <th className="py-4 px-4 font-label-sm text-label-sm text-on-surface-variant font-medium uppercase tracking-wider">Invoice #</th>
                    <th className="py-4 px-4 font-label-sm text-label-sm text-on-surface-variant font-medium uppercase tracking-wider">Quote Ref</th>
                    <th className="py-4 px-4 font-label-sm text-label-sm text-on-surface-variant font-medium uppercase tracking-wider">Invoice Date</th>
                    <th className="py-4 px-4 font-label-sm text-label-sm text-on-surface-variant font-medium uppercase tracking-wider">Uploaded</th>
                    <th className="py-4 px-4"></th>
                  </tr>
                </thead>
                <tbody className="font-body-md text-body-md">
                  {invoices.map((inv) => (
                    <tr
                      key={inv.id}
                      className="border-b border-surface-container hover:bg-surface-container/30 transition-colors group cursor-pointer"
                      onClick={() => navigate(`/app/invoices/${inv.id}`)}
                    >
                      <td className="py-4 px-4 font-mono text-apple-blue font-medium text-sm">{inv.invoice_number}</td>
                      <td className="py-4 px-4 font-mono text-on-surface-variant text-label-sm">{inv.quote?.quote_ref ?? '—'}</td>
                      <td className="py-4 px-4 text-on-surface-variant text-sm">{inv.invoice_date}</td>
                      <td className="py-4 px-4 text-outline-variant text-sm">
                        {new Date(inv.uploaded_at).toLocaleDateString()}
                      </td>
                      <td className="py-4 px-4 text-right">
                        <button className="text-on-surface-variant hover:text-primary opacity-0 group-hover:opacity-100 transition-opacity">
                          <span className="material-symbols-outlined text-[20px]">arrow_forward</span>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
