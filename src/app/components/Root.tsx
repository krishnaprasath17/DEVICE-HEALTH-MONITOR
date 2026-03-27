import { Outlet } from "react-router";
import { BottomNav } from "./BottomNav";
import { TopBar } from "./TopBar";

export function Root() {
  return (
    <div className="dark min-h-screen bg-[#0c0e10] font-['Inter'] select-none">
      <TopBar />
      <Outlet />
      <BottomNav />
    </div>
  );
}
