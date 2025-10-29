import { useState, useEffect, type ChangeEvent } from "react";

type AnalyzeResult = { valence: number; arousal: number };
type BuildResult = {
  valence: number;
  arousal: number;
  mix_url: string;                 // ex: /static/renders/mix.wav
  picks?: Record<string, { path: string; bpm: number | null; key: string | null; valence: number; arousal: number }>;
};

export default function Upload() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);         // upload
  const [busy, setBusy] = useState(false);               // analyse / build
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<AnalyzeResult | null>(null);
  const [mixUrl, setMixUrl] = useState<string | null>(null);
  const [picks, setPicks] = useState<BuildResult["picks"] | null>(null);

  const API = import.meta.env.VITE_API_URL ?? ""; // ex: http://localhost:8000

  const onPick = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] ?? null;
    setFile(f);
    setMsg(null);
    setErr(null);
    setAnalysis(null);
    setMixUrl(null);
    setPicks(null);
    setPreview(f ? URL.createObjectURL(f) : null);
    console.log("[pick]", f?.name, f?.type, f?.size);
  };

  useEffect(() => {
    return () => {
      if (preview) URL.revokeObjectURL(preview);
    };
  }, [preview]);

  const onUpload = async () => {
    if (!file) return;
    setLoading(true);
    setMsg(null);
    setErr(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(`${API}/api/upload-image`, { method: "POST", body: fd });
      const text = await res.text();
      console.log("[upload] status", res.status, text);
      if (!res.ok) throw new Error(text || `HTTP ${res.status}`);
      const json = JSON.parse(text);
      setMsg(`✅ Image envoyée : ${json.saved_as ?? json.message ?? "OK"}`);
    } catch (e: any) {
      setErr(e?.message ?? "Échec de l’upload");
    } finally {
      setLoading(false);
    }
  };

  const onAnalyze = async () => {
    if (!file) return;
    setBusy(true);
    setErr(null);
    setAnalysis(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(`${API}/api/analyze-image`, { method: "POST", body: fd });
      if (!res.ok) throw new Error(await res.text());
      const json = (await res.json()) as AnalyzeResult;
      setAnalysis(json);
    } catch (e: any) {
      setErr(e?.message ?? "Échec de l’analyse");
    } finally {
      setBusy(false);
    }
  };

  const onBuild = async () => {
    if (!file) return;
    setBusy(true);
    setErr(null);
    setMsg(null);
    setMixUrl(null);
    setPicks(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(`${API}/api/build-track`, { method: "POST", body: fd });
      if (!res.ok) throw new Error(await res.text());
      const json = (await res.json()) as BuildResult;
      setAnalysis({ valence: json.valence, arousal: json.arousal });
      const fullUrl = (API ? API.replace(/\/+$/, "") : "") + json.mix_url; // concat sûre
      setMixUrl(fullUrl);
      setPicks(json.picks ?? null);
      setMsg("🎵 Prod générée !");
    } catch (e: any) {
      setErr(e?.message ?? "Échec de la création de la prod");
    } finally {
      setBusy(false);
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

        <div className="grid grid-cols-3 gap-3">
          <button
            type="submit"
            disabled={!file || loading}
            className="w-full px-4 py-2 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 disabled:opacity-50 transition-all"
          >
            {loading ? "Envoi…" : "Envoyer"}
          </button>

          <button
            type="button"
            onClick={onAnalyze}
            disabled={!file || busy}
            className="w-full px-4 py-2 rounded-lg bg-emerald-600 text-white font-semibold hover:bg-emerald-700 disabled:opacity-50 transition-all"
          >
            {busy ? "Analyse…" : "Analyser"}
          </button>

          <button
            type="button"
            onClick={onBuild}
            disabled={!file || busy}
            className="w-full px-4 py-2 rounded-lg bg-purple-600 text-white font-semibold hover:bg-purple-700 disabled:opacity-50 transition-all"
          >
            {busy ? "Création…" : "Créer une prod"}
          </button>
        </div>
      </form>

      {analysis && (
        <div className="rounded-lg border border-emerald-600/40 p-3 text-sm">
          <p>
            Valence : <b>{analysis.valence.toFixed(2)}</b> • Arousal :{" "}
            <b>{analysis.arousal.toFixed(2)}</b>
          </p>
        </div>
      )}

      {mixUrl && (
        <div className="rounded-lg border border-purple-600/40 p-3 text-sm space-y-2">
          <audio controls src={mixUrl} className="w-full" />
          <a className="underline" href={mixUrl} download>Télécharger</a>
          {picks && (
            <details className="mt-2">
              <summary className="cursor-pointer">Samples utilisés</summary>
              <ul className="list-disc pl-5">
                {Object.entries(picks).map(([typ, p]) => (
                  <li key={typ}>
                    <b>{typ}</b> — {p.path} {p.key ? `(${p.key})` : ""} {p.bpm ? `• ${p.bpm} BPM` : ""}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      )}

      {msg && <p className="text-green-400 text-sm">{msg}</p>}
      {err && <p className="text-red-400 text-sm">{err}</p>}
    </div>
  );
}
