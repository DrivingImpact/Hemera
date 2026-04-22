import { getHemeraUser } from "@/lib/auth";
import { SupplierList } from "./supplier-list";

export default async function SuppliersPage() {
  const user = await getHemeraUser();

  if (user?.role !== "admin") {
    return (
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="bg-surface rounded-xl border border-[#E5E5E0] p-8 text-center">
          <h3 className="text-lg font-semibold mb-1">Admin Access Required</h3>
          <p className="text-muted text-sm">
            Contact your account manager if you need access.
          </p>
        </div>
      </div>
    );
  }

  return <SupplierList />;
}
