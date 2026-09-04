export default function Header() {
  return (
    <header className="w-full border-b border-outline-variant/60 bg-surface-container-lowest/80 backdrop-blur-md transition-all">
      <div className="max-w-[1800px] mx-auto px-6 sm:px-10 lg:px-16 h-24 flex items-center justify-center">
        {/* Brand Logo & Identity */}
        <div className="flex items-center gap-5">
          {/* Logo */}
          <img src="/logo.png" alt="DeNoiZ Logo" className="w-12 h-12 object-contain rounded-full" />
          <div className="flex flex-col justify-center">
            <h1 className="text-3xl font-bold font-headline tracking-tight text-on-surface leading-none mb-1">DeNoi<span className="text-[#0ce079] italic">Z</span></h1>
            <p className="text-sm font-medium text-on-surface-variant/90 tracking-wide">Defense-grade noise suppression in real time</p>
          </div>
        </div>
      </div>
    </header>
  );
}
