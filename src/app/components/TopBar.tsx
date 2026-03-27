export function TopBar() {
  return (
    <header className="fixed top-0 w-full z-50 bg-[#0c0e10]/60 backdrop-blur-md flex justify-between items-center px-6 h-16">
      <div className="flex items-center gap-2">
        <span className="material-symbols-outlined text-[#cafd00]">location_on</span>
        <span className="font-['Epilogue'] font-bold tracking-tight text-[#eeeef0]">
          Indiranagar, Bangalore
        </span>
      </div>
      <div className="flex items-center gap-4">
        <button className="active:scale-95 duration-200 hover:opacity-80 transition-opacity">
          <span className="material-symbols-outlined text-[#eeeef0]">notifications</span>
        </button>
        <div className="w-8 h-8 rounded-full bg-[#1d2022] border border-[#46484a] overflow-hidden">
          <img
            className="w-full h-full object-cover"
            alt="User profile"
            src="https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&h=100&fit=crop"
          />
        </div>
      </div>
    </header>
  );
}
