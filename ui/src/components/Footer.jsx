import React from 'react';

export default function Footer() {
  return (
    <footer className="w-full border-t border-outline-variant/60 bg-surface-container-lowest/70 backdrop-blur-md py-3.5 mt-auto">
      <div className="max-w-[1800px] mx-auto px-6 sm:px-10 lg:px-16 flex items-center justify-center gap-2 text-sm text-on-surface-variant">
        <span className="font-bold text-on-surface font-headline tracking-wide">DeNoiZ</span>
        <span>•</span>
        <span>Defense-grade noise suppression in real time</span>
      </div>
    </footer>
  );
}
