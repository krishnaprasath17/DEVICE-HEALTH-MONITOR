import { createBrowserRouter } from "react-router";
import { Root } from "./components/Root";
import { Home } from "./pages/Home";
import { Discovery } from "./pages/Discovery";
import { Community } from "./pages/Community";
import { Bookings } from "./pages/Bookings";
import { Profile } from "./pages/Profile";
import { VenueDetail } from "./pages/VenueDetail";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Root,
    children: [
      { index: true, Component: Home },
      { path: "discovery", Component: Discovery },
      { path: "community", Component: Community },
      { path: "bookings", Component: Bookings },
      { path: "profile", Component: Profile },
      { path: "venue/:id", Component: VenueDetail },
    ],
  },
]);
