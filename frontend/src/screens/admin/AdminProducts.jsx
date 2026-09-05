import { useEffect, useState } from "react";
import { Plus, Package, CheckCircle2, X, Pencil } from "lucide-react";
import { getProducts, createProduct, updateProduct } from "../../api/client";
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
  quantity_on_hand: "",
  is_promoted: false,
  promo_tag: "",
};

function formFromProduct(p) {
  return {
    name: p.name,
    product_code: p.product_code,
    category: p.category,
    price: p.price,
    cost: p.cost ?? "",
    unit: p.unit,
    tax_pct: p.tax_pct,
    description: p.description || "",
    quantity_on_hand: p.quantity_on_hand ?? "",
    is_promoted: p.is_promoted,
    promo_tag: p.promo_tag || "",
  };
}

export default function AdminProducts() {
  const { toast } = useToast();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null); // full product object, or null when creating
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
    { key: "actions", label: "" },
  ];

  const load = () => getProducts().then(setProducts);

  useEffect(() => {
    load().finally(() => setLoading(false));
  }, []);

  const filtered = products.filter((p) => filter === "all" || p.category.toLowerCase() === filter);

  const openCreate = () => {
    setEditingProduct(null);
    setFormData(emptyForm);
    setIsModalOpen(true);
  };

  const openEdit = (product) => {
    setEditingProduct(product);
    setFormData(formFromProduct(product));
    setIsModalOpen(true);
  };

  const handleSubmit = async (e) => {
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
        cost: formData.cost !== "" ? Number(formData.cost) : null,
        unit: formData.unit,
        tax_pct: Number(formData.tax_pct || 0),
        description: formData.description || null,
        is_subscription: formData.category === "Subscription",
        recurring_cycle: formData.category === "Subscription" ? "Monthly" : null,
        quantity_on_hand: formData.quantity_on_hand !== "" ? Number(formData.quantity_on_hand) : null,
        is_promoted: formData.is_promoted,
        promo_tag: formData.is_promoted ? (formData.promo_tag || null) : null,
        // PATCH replaces the whole product, including nested rows -- carry
        // the existing variants/price lists through untouched so editing a
        // base field (price, tax, etc.) doesn't silently wipe them.
        variants: editingProduct
          ? editingProduct.variants.map((v) => ({ attribute: v.attribute, value: v.value, extra_price: v.extra_price }))
          : [],
        price_lists: editingProduct
          ? editingProduct.price_list_entries.map((p) => ({
              customer_tier: p.customer_tier, currency: p.currency, price_rule: p.price_rule,
            }))
          : [],
      };

      if (editingProduct) {
        const updated = await updateProduct(editingProduct.id, payload);
        setProducts((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
        toast(`Product "${updated.name}" updated.`, "success");
      } else {
        const created = await createProduct(payload);
        setProducts((prev) => [created, ...prev]);
        toast(`Product "${created.name}" (${created.product_code}) added to catalog.`, "success");
      }
      setIsModalOpen(false);
      setEditingProduct(null);
      setFormData(emptyForm);
    } catch (err) {
      toast(err.message || "Could not save product.", "error");
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
            body: "Products created or edited here are immediately reflected in the quotation builder's product picker.",
          }}
          action={
            <button onClick={openCreate} className="df-btn-primary gap-1.5 shadow-sm" aria-label="Add new product to catalog">
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
            if (column.key === "actions") return (
              <button
                onClick={() => openEdit(row)}
                className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[11px] font-bold text-slate-500 hover:bg-slate-100 hover:text-slate-800"
                aria-label={`Edit ${row.name}`}
              >
                <Pencil className="h-3 w-3" /> Edit
              </button>
            );
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
                  <h2 className="text-base font-bold text-slate-900">{editingProduct ? "Edit Product" : "Add New Product"}</h2>
                  <p className="text-[11px] text-slate-500">
                    {editingProduct ? `Updates via PATCH /products/${editingProduct.id}` : "Creates a real row via POST /products"}
                  </p>
                </div>
              </div>
              <button onClick={() => setIsModalOpen(false)} className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100" aria-label="Close modal">
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-3.5">
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
                  <label className="df-label">Base Price (₹) *</label>
                  <input required type="number" min="0" step="0.01" className="df-input text-xs font-mono" value={formData.price} onChange={(e) => setFormData({ ...formData, price: e.target.value })} />
                </div>
                <div>
                  <label className="df-label">Cost (₹)</label>
                  <input type="number" min="0" step="0.01" className="df-input text-xs font-mono" value={formData.cost} onChange={(e) => setFormData({ ...formData, cost: e.target.value })} />
                </div>
                <div>
                  <label className="df-label">Tax Rate (%)</label>
                  <input type="number" min="0" max="100" className="df-input text-xs font-mono" value={formData.tax_pct} onChange={(e) => setFormData({ ...formData, tax_pct: e.target.value })} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="df-label">Unit</label>
                  <input className="df-input text-xs" value={formData.unit} onChange={(e) => setFormData({ ...formData, unit: e.target.value })} />
                </div>
                <div>
                  <label className="df-label">Stock on Hand</label>
                  <input type="number" min="0" className="df-input text-xs font-mono" value={formData.quantity_on_hand} onChange={(e) => setFormData({ ...formData, quantity_on_hand: e.target.value })} />
                </div>
              </div>
              <div>
                <label className="df-label">Description</label>
                <textarea rows="2" className="df-input text-xs" value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} />
              </div>
              <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50/60 px-3 py-2.5">
                <input
                  id="is_promoted" type="checkbox" className="h-3.5 w-3.5"
                  checked={formData.is_promoted}
                  onChange={(e) => setFormData({ ...formData, is_promoted: e.target.checked })}
                />
                <label htmlFor="is_promoted" className="text-xs font-semibold text-slate-700">Promoted item</label>
                {formData.is_promoted && (
                  <input
                    className="df-input text-xs flex-1" placeholder="Promo tag, e.g. Q4 Bundle"
                    value={formData.promo_tag}
                    onChange={(e) => setFormData({ ...formData, promo_tag: e.target.value })}
                  />
                )}
              </div>
              <div className="mt-5 flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                <button type="button" onClick={() => setIsModalOpen(false)} className="df-btn-secondary">Cancel</button>
                <button type="submit" disabled={saving} className="df-btn-primary gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  <span>{saving ? "Saving..." : editingProduct ? "Save Changes" : "Save to Catalog"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
