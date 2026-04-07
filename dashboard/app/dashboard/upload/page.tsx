import { UploadDropzone } from "@/components/upload/dropzone";

export default function UploadPage() {
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Upload Spend Data</h1>
        <p className="text-muted text-sm mt-0.5">
          Upload a CSV or Excel file to create a new engagement. We&apos;ll classify
          emissions and match suppliers automatically.
        </p>
      </div>

      <div className="bg-surface rounded-xl border border-[#E5E5E0] p-6">
        <UploadDropzone />
      </div>

      <div className="bg-paper rounded-lg border border-[#E5E5E0] p-4">
        <h4 className="text-xs font-semibold uppercase tracking-[0.5px] mb-3">
          Expected Format
        </h4>
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr>
              {["date", "supplier", "description", "amount_gbp"].map((col) => (
                <th
                  key={col}
                  className="text-left px-2 py-1.5 bg-[#F0F0EB] font-mono font-semibold border border-[#E5E5E0]"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              {["2024-01-15", "Heathrow Express", "Rail travel LHR", "42.50"].map((v, i) => (
                <td key={i} className="px-2 py-1.5 border border-[#E5E5E0] text-muted font-mono">
                  {v}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
