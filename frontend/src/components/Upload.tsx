import { useState } from "react";

export default function Upload() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const onPick = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] ?? null;
    setFile(f);
    setMsg(null);
    setErr(null);
    setPreview(f ? URL.createObjectURL(f) : null);
    console.log("[pick]", f?.name, f?.type, f?.size);
  };

  const onUpload = async () => {
    if (!file) return;
    setLoading(true);
    setMsg(null);
    setErr(null);
    try {
      const fd = new FormData();
      fd.append("file", file);

      const res = await fetch("/api/upload-image", { method: "POST", body: fd });
      const text = await res.text();
      console.log("[upload] status", res.status, text);
      if (!res.ok) throw new Error(text || `HTTP ${res.status}`);

      const json = JSON.parse(text);
      setMsg(`✅ Image envoyée : ${json.saved_as ?? json.message}`);
    } catch (e: any) {
      setErr(e?.message ?? "Échec de l’upload");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full space-y-4">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onUpload();
        }}
        className="space-y-3 w-full"
      >
        <label className="block">
          <span className="sr-only">Choisir une image</span>
          <input
            type="file"
            name="file"
            accept="image/*"
            onChange={onPick}
            className="block w-full text-sm text-gray-200
              file:me-4 file:py-2 file:px-4
              file:rounded-lg file:border-0
              file:text-sm file:font-semibold
              file:bg-blue-600 file:text-white
              hover:file:bg-blue-700
              file:disabled:opacity-50 file:disabled:pointer-events-none
              dark:text-neutral-400 dark:file:bg-blue-500 dark:hover:file:bg-blue-400"
          />
        </label>

        {preview && (
          <img
            src={preview}
            alt="preview"
            className="mt-3 max-h-48 rounded-lg shadow-md"
          />
        )}

        <button
          type="submit"
          disabled={!file || loading}
          className="w-full px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-50 transition-all"
        >
          {loading ? "Envoi…" : "Envoyer"}
        </button>
      </form>

      {msg && <p className="text-green-400 text-sm">{msg}</p>}
      {err && <p className="text-red-400 text-sm">{err}</p>}
    </div>
  );
}
