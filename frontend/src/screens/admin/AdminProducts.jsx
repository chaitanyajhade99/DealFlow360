import { useEffect, useState } from "react";
import { Plus, Package, CheckCircle2, X } from "lucide-react";
import { getProducts, createProduct } from "../../api/client";
import AdminNav from "../../components/AdminNav";
import ListScreen from "../../components/ListScreen";
import StatusBadge from "../../components/StatusBadge";
import Skeleton from "../../components/Skeleton";
import { useToast } from "../../context/ToastContext";
import { money, pct } from "../../utils";

const emptyForm = {
  name: "",
  product_code: "",
  category: "Hardware",
  price: "",
  cost: "",
  unit: "each",
  tax_pct: "8",
  description: "",
};

export default function AdminProducts() {
  const { toast } = useToast();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState(emptyForm);

  const columns = [
    { key: "product_code", label: "SKU / Code" },
    { key: "name", label: "Product Name" },
    { key: "category", label: "Category" },
    { key: "price", label: "Base Price" },
    { key: "cost", label: "Cost" },
    { key: "unit", label: "Unit" },
    { key: "tax_pct", label: "Tax %" },
    { key: "is_promoted", label: "Promoted" },
  ];

  const load = () => getProducts().then(setProducts);

  useEffect(() => {
    load().finally(() => setLoading(false));
  }, []);

  const filtered = products.filter((p) => filter === "all" || p.category.toLowerCase() === filter);

  const handleAddProduct = async (e) => {
    e.preventDefault();
    if (!formData.name.trim() || !formData.price || !formData.product_code.trim()) {
      toast("Provide a product code, name, and price.", "warning");
      return;
    }
    setSaving(true);
    try {
      const payload = {
        product_code: formData.product_code,
        name: formData.name,
        category: formData.category,
        price: Number(formData.price),
        cost: formData.cost ? Number(formData.cost) : null,
        unit: formData.unit,
        tax_pct: Number(formData.tax_pct || 0),
        description: formData.description || null,
        is_subscription: formData.category === "Subscription",
        recurring_cycle: formData.category === "Subscription" ? "Monthly" : null,
      };
      const created = await createProduct(payload);
      setProducts((prev) => [created, ...prev]);
      setIsModalOpen(false);
      setFormData(emptyForm);
      toast(`Product "${created.name}" (${created.product_code}) added to catalog.`, "success");
    } catch (err) {
      toast(err.message || "Could not create product.", "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <AdminNav />
      {loading ? (
        <Skeleton variant="card" count={3} />
      ) : (
        <ListScreen
          title="Product Catalog & Master Price List"
          subtitle="Manage sellable hardware SKUs, service plans, and subscriptions (PDF A2)."
          filters={[
            { label: "All Items", value: "all" },
            { label: "Hardware", value: "hardware" },
            { label: "Services", value: "services" },
            { label: "Subscription", value: "subscription" },
          ]}
          activeFilter={filter}
          onFilterChange={setFilter}
          columns={columns}
          rows={filtered}
          banner={{
            title: "Live product catalog:",
            body: "Products created here are immediately available in the quotation builder's product picker.",
          }}
          action={
            <button onClick={() => setIsModalOpen(true)} className="df-btn-primary gap-1.5 shadow-sm" aria-label="Add new product to catalog">
              <Plus className="h-4 w-4" />
              <span>+ New Product</span>
            </button>
          }
          renderCell={(row, column) => {
            if (column.key === "product_code") return <span className="font-mono text-xs font-bold text-brand-700">{row.product_code}</span>;
            if (column.key === "name") return (
              <div>
                <div className="font-bold text-xs text-slate-900">{row.name}</div>
                <div className="text-[11px] text-slate-400 truncate max-w-xs">{row.description || "Standard commercial SKU"}</div>
              </div>
            );
            if (column.key === "category") return <span className="rounded bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-700">{row.category}</span>;
            if (column.key === "price") return <span className="font-mono text-xs font-bold text-slate-900">{money(row.price)}</span>;
            if (column.key === "cost") return <span className="font-mono text-xs text-slate-600">{row.cost != null ? money(row.cost) : "—"}</span>;
            if (column.key === "unit") return <span className="text-xs text-slate-600">{row.unit}</span>;
            if (column.key === "tax_pct") return <span className="font-mono text-xs text-slate-600">{pct(row.tax_pct)}</span>;
            if (column.key === "is_promoted") return row.is_promoted ? <StatusBadge value="active" className="!bg-amber-50 !text-amber-800 !border-amber-200" /> : <span className="text-xs text-slate-300">—</span>;
            return row[column.key];
          }}
        />
      )}

      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 animate-fade-slide-in">
          <div className="relative w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl border border-slate-200 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3 mb-4">
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-50 text-brand-700">
                  <Package className="h-4 w-4" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-slate-900">Add New Product</h2>
                  <p className="text-[11px] text-slate-500">Creates a real row via POST /products</p>
                </div>
              </div>
              <button onClick={() => setIsModalOpen(false)} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100" aria-label="Close modal">
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleAddProduct} className="space-y-3.5">
              <div>
                <label className="df-label">Product Name *</label>
                <input required className="df-input text-xs" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="df-label">SKU / Product Code *</label>
                  <input required className="df-input text-xs font-mono" value={formData.product_code} onChange={(e) => setFormData({ ...formData, product_code: e.target.value })} />
                </div>
                <div>
                  <label className="df-label">Category *</label>
                  <select className="df-input text-xs" value={formData.category} onChange={(e) => setFormData({ ...formData, category: e.target.value })}>
                    <option value="Hardware">Hardware</option>
                    <option value="Services">Services</option>
                    <option value="Subscription">Subscription</option>
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="df-label">Base Price ($) *</label>
                  <input required type="number" min="0" step="0.01" className="df-input text-xs font-mono" value={formData.price} onChange={(e) => setFormData({ ...formData, price: e.target.value })} />
                </div>
                <div>
                  <label className="df-label">Cost ($)</label>
                  <input type="number" min="0" step="0.01" className="df-input text-xs font-mono" value={formData.cost} onChange={(e) => setFormData({ ...formData, cost: e.target.value })} />
                </div>
                <div>
                  <label className="df-label">Tax Rate (%)</label>
                  <input type="number" min="0" max="100" className="df-input text-xs font-mono" value={formData.tax_pct} onChange={(e) => setFormData({ ...formData, tax_pct: e.target.value })} />
                </div>
              </div>
              <div>
                <label className="df-label">Description</label>
                <textarea rows="2" className="df-input text-xs" value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} />
              </div>
              <div className="mt-5 flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                <button type="button" onClick={() => setIsModalOpen(false)} className="df-btn-secondary">Cancel</button>
                <button type="submit" disabled={saving} className="df-btn-primary gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  <span>{saving ? "Saving..." : "Save to Catalog"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
