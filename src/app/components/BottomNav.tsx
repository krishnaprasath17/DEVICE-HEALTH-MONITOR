import { useLocation, useNavigate } from "react-router";

export function BottomNav() {
  const location = useLocation();
  const navigate = useNavigate();

  const navItems = [
    { path: "/", icon: "home", label: "Home" },
    { path: "/discovery", icon: "explore", label: "Discovery" },
    { path: "/community", icon: "groups", label: "Community" },
    { path: "/bookings", icon: "event_available", label: "Bookings" },
    { path: "/profile", icon: "person", label: "Profile" },
  ];

  return (
    <nav className="fixed bottom-0 w-full z-50 rounded-t-[2rem] bg-[#0c0e10] border-t border-[#eeeef0]/10 shadow-[0_-4px_24px_rgba(0,0,0,0.4)] flex justify-around items-center h-20 px-4 pb-2">
      {navItems.map((item) => {
        const isActive = location.pathname === item.path;
        return (
          <button
            key={item.path}
            onClick={() => navigate(item.path)}
            className={`flex flex-col items-center justify-center px-4 py-1.5 active:scale-90 duration-200 transition-all ${
              isActive
                ? "bg-[#cafd00] text-[#0c0e10] rounded-xl"
                : "text-[#eeeef0]/60 hover:text-[#cafd00]"
            }`}
          >
            <span 
              className="material-symbols-outlined"
              style={isActive ? { fontVariationSettings: "'FILL' 1" } : {}}
            >
              {item.icon}
            </span>
            <span className="text-[10px] font-medium font-['Inter'] uppercase tracking-widest mt-1">
              {item.label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}
