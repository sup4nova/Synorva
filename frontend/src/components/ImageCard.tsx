import type { ReactNode } from "react";

type Props = {
  title?: string;
  children: ReactNode;
};

const ImageCard = ({ title = "Dépose ton document", children }: Props) => (
  <div className="bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl shadow-2xl p-8 w-[500px] text-white">
    {title && <h2 className="text-3xl font-bold mb-6 text-center">{title}</h2>}
    <div className="flex flex-col items-center">{children}</div>
  </div>
);

export default ImageCard;
