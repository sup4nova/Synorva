import { Routes, Route } from "react-router-dom";
import GradientBackground from "./components/GradientBackground";
import ImageCard from "./components/ImageCard";
import Upload from "./components/Upload";

export default function App() {
  return (
    <>
      {/* 🌈 Fond animé */}
      <div className="fixed inset-0 -z-10 pointer-events-none">
        <GradientBackground />
      </div>

      {/* 🧭 Routes */}
      <Routes>
        <Route
          path="/"
          element={
            <main className="relative z-10 min-h-screen flex items-center justify-center p-6">
              {/* ✅ Une seule carte contenant le formulaire d’upload */}
              <ImageCard>
                <Upload />
              </ImageCard>
            </main>
          }
        />
      </Routes>
    </>
  );
}
