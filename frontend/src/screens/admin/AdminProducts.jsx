import { useState } from "react";
import { Plus, Package, CheckCircle2, X, Tag } from "lucide-react";
import { products as initialProducts } from "../../api/mockData";
import ListScreen from "../../components/ListScreen";
import StatusBadge from "../../components/StatusBadge";
import { useToast } from "../../context/ToastContext";
import { money, pct } from "../../utils";

export default function AdminProducts() {
  const { toast } = useToast();
  const [productList, setProductList] = useState(initialProducts);
  const [filter, setFilter] = useState("all");
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Form State
  const [formData, setFormData] = useState({
    name: "",
    product_code: "",
    category: "Hardware",
    price: "",
    unit: "each",
    tax_pct: "8",
    description: "",
  });

  const columns = [
    { key: "product_code", label: "SKU / Code" },
    { key: "name", label: "Product Name" },
    { key: "category", label: "Category" },
    { key: "price", label: "Base Price" },
    { key: "unit", label: "Unit" },
    { key: "tax_pct", label: "Tax %" },
    { key: "status", label: "Catalog Status" },
  ];

  const filtered = productList.filter((p) => {
    if (filter === "all") return true;
    return p.category.toLowerCase() === filter.toLowerCase();
  });

  const handleAddProduct = (e) => {
    e.preventDefault();
    if (!formData.name.trim() || !formData.price) {
      toast("Please provide at least a product name and price.", "warning");
      return;
    }

    const newProd = {
      id: Date.now(),
      product_code: formData.product_code || formData.name.toUpperCase().replace(/\s+/g, "-"),
      name: formData.name,
      category: formData.category,
      price: Number(formData.price),
      unit: formData.unit,
      tax_pct: Number(formData.tax_pct || 0),
      description: formData.description,
      is_subscription: formData.category === "Subscription" || formData.category === "Services",
      recurring_cycle: formData.category === "Subscription" ? "Yearly" : null,
      quantity_on_hand: 25,
      status: "active",
    };

    setProductList((prev) => [newProd, ...prev]);
    setIsModalOpen(false);
    setFormData({
      name: "",
      product_code: "",
      category: "Hardware",
      price: "",
      unit: "each",
      tax_pct: "8",
      description: "",
    });
    toast(`Product "${newProd.name}" (${newProd.product_code}) added to catalog.`, "success");
  };

  return (
    <>
      <ListScreen
        title="Product Catalog & Master Price List"
        subtitle="Manage sellable hardware SKUs, software tiers, and service warranty plans."
        filters={[
          { label: "All Items", value: "all" },
          { label: "Hardware", value: "hardware" },
          { label: "Services", value: "services" },
          { label: "Software", value: "software" },
        ]}
        activeFilter={filter}
        onFilterChange={setFilter}
        columns={columns}
        rows={filtered}
        banner={{
          title: "Admin Governance Area:",
          body: "Changes to product master records immediately reflect across new quotation line builders and margin guardrail calculations.",
        }}
        action={
          <button
            onClick={() => setIsModalOpen(true)}
            className="df-btn-primary gap-1.5 shadow-sm"
            aria-label="Add new product to catalog"
          >
            <Plus className="h-4 w-4" />
            <span>+ New Product</span>
          </button>
        }
        renderCell={(row, column) => {
          if (column.key === "product_code") {
            return (
              <span className="font-mono text-xs font-bold text-brand-700">
                {row.product_code}
              </span>
            );
          }
          if (column.key === "name") {
            return (
              <div>
                <div className="font-bold text-xs text-slate-900">{row.name}</div>
                <div className="text-[11px] text-slate-400 truncate max-w-xs">
                  {row.description || "Standard commercial SKU"}
                </div>
              </div>
            );
          }
          if (column.key === "category") {
            return (
              <span className="rounded bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-700">
                {row.category}
              </span>
            );
          }
          if (column.key === "price") {
            return (
              <span className="font-mono text-xs font-bold text-slate-900">
                {money(row.price)}
              </span>
            );
          }
          if (column.key === "unit") {
            return <span className="text-xs text-slate-600">{row.unit}</span>;
          }
          if (column.key === "tax_pct") {
            return (
              <span className="font-mono text-xs text-slate-600">
                {pct(row.tax_pct)}
              </span>
            );
          }
          if (column.key === "status") {
            return <StatusBadge value={row.status || "active"} />;
          }
          return row[column.key];
        }}
      />

      {/* New Product Modal */}
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
                  <p className="text-[11px] text-slate-500">Create a SKU entry in the catalog</p>
                </div>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
                aria-label="Close modal"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleAddProduct} className="space-y-3.5">
              <div>
                <label className="df-label">Product Name *</label>
                <input
                  required
                  className="df-input text-xs"
                  placeholder="e.g. Enterprise Router 48-Port"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="df-label">SKU / Product Code</label>
                  <input
                    className="df-input text-xs font-mono"
                    placeholder="ROUTER-48-ENT"
                    value={formData.product_code}
                    onChange={(e) => setFormData({ ...formData, product_code: e.target.value })}
                  />
                </div>
                <div>
                  <label className="df-label">Category *</label>
                  <select
                    className="df-input text-xs"
                    value={formData.category}
                    onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  >
                    <option value="Hardware">Hardware</option>
                    <option value="Services">Services</option>
                    <option value="Software">Software</option>
                    <option value="Subscription">Subscription</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="df-label">Base Price ($) *</label>
                  <input
                    required
                    type="number"
                    min="0"
                    step="0.01"
                    className="df-input text-xs font-mono"
                    placeholder="999.00"
                    value={formData.price}
                    onChange={(e) => setFormData({ ...formData, price: e.target.value })}
                  />
                </div>
                <div>
                  <label className="df-label">Unit</label>
                  <select
                    className="df-input text-xs"
                    value={formData.unit}
                    onChange={(e) => setFormData({ ...formData, unit: e.target.value })}
                  >
                    <option value="each">each</option>
                    <option value="seat">seat</option>
                    <option value="license">license</option>
                    <option value="hour">hour</option>
                  </select>
                </div>
                <div>
                  <label className="df-label">Tax Rate (%)</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    className="df-input text-xs font-mono"
                    value={formData.tax_pct}
                    onChange={(e) => setFormData({ ...formData, tax_pct: e.target.value })}
                  />
                </div>
              </div>

              <div>
                <label className="df-label">Description</label>
                <textarea
                  rows="2"
                  className="df-input text-xs"
                  placeholder="Technical specifications and warranty terms..."
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                />
              </div>

              <div className="mt-5 flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="df-btn-secondary"
                >
                  Cancel
                </button>
                <button type="submit" className="df-btn-primary gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  <span>Save to Catalog</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
