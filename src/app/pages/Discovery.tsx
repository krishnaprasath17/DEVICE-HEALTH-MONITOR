import { useState } from "react";
import { useNavigate } from "react-router";

export function Discovery() {
  const navigate = useNavigate();
  const [activeSport, setActiveSport] = useState("all");

  const sports = [
    { id: "all", label: "All Sports", icon: "star" },
    { id: "badminton", label: "Badminton" },
    { id: "football", label: "Football" },
    { id: "cricket", label: "Cricket" },
    { id: "tennis", label: "Tennis" },
  ];

  const venues = [
    {
      id: 1,
      name: "Indiranagar Sports Club",
      image: "https://images.unsplash.com/photo-1626224583764-f87db24ac4ea?w=800&h=600&fit=crop",
      rating: 4.8,
      distance: "1.2 km",
      sports: "Badminton, Squash",
      price: 450,
      slotsLeft: 5,
    },
    {
      id: 2,
      name: "The Arena Rooftop Turf",
      image: "https://images.unsplash.com/photo-1575361204480-aadea25e6e68?w=800&h=600&fit=crop",
      rating: 4.6,
      distance: "2.8 km",
      sports: "Football (5v5)",
      price: 1200,
      lastBooked: "2h ago",
    },
  ];

  return (
    <main className="pt-20 pb-28 px-6 min-h-screen">
      {/* Search */}
      <section className="mb-8">
        <div className="relative group">
          <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
            <span className="material-symbols-outlined text-[#aaabad]">search</span>
          </div>
          <input
            className="w-full bg-[#1d2022] border-none rounded-xl py-4 pl-12 pr-4 text-[#eeeef0] focus:ring-2 focus:ring-[#cafd00] transition-all placeholder:text-[#aaabad]/50"
            placeholder="Search venues, sports, or teams..."
            type="text"
          />
        </div>
      </section>

      {/* Sport Chips */}
      <section className="mb-10">
        <div className="flex overflow-x-auto scrollbar-hide gap-3 pb-2">
          {sports.map((sport) => (
            <button
              key={sport.id}
              onClick={() => setActiveSport(sport.id)}
              className={`flex-none px-6 py-2.5 rounded-lg font-medium text-sm flex items-center gap-2 transition-colors ${
                activeSport === sport.id
                  ? "bg-[#6affc9] text-[#006045]"
                  : "bg-[#1d2022] text-[#eeeef0] hover:bg-[#232629]"
              }`}
            >
              {sport.icon && (
                <span
                  className="material-symbols-outlined text-sm"
                  style={{ fontVariationSettings: "'FILL' 1" }}
                >
                  {sport.icon}
                </span>
              )}
              {sport.label}
            </button>
          ))}
        </div>
      </section>

      {/* Nearby Venues */}
      <section>
        <div className="flex justify-between items-end mb-6">
          <h2 className="font-['Epilogue'] text-3xl font-extrabold tracking-tight">
            Nearby <span className="text-[#cafd00]">Venues</span>
          </h2>
          <button className="text-[#cafd00] text-sm font-semibold uppercase tracking-widest">
            See Map
          </button>
        </div>

        <div className="grid grid-cols-1 gap-6">
          {venues.map((venue) => (
            <div
              key={venue.id}
              onClick={() => navigate(`/venue/${venue.id}`)}
              className="group relative bg-[#111416] rounded-xl overflow-hidden active:scale-[0.98] transition-all duration-300 cursor-pointer"
            >
              <div className="aspect-[16/9] w-full relative">
                <img
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
                  alt={venue.name}
                  src={venue.image}
                />
                <div className="absolute inset-0 bg-gradient-to-t from-[#111416] via-transparent to-transparent"></div>
                {venue.slotsLeft && (
                  <div className="absolute top-4 right-4 bg-[#cafd00] text-[#4a5e00] px-3 py-1 rounded-full text-xs font-bold flex items-center gap-1">
                    <span
                      className="material-symbols-outlined text-xs"
                      style={{ fontVariationSettings: "'FILL' 1" }}
                    >
                      bolt
                    </span>
                    {venue.slotsLeft} SLOTS LEFT
                  </div>
                )}
                {venue.lastBooked && (
                  <div className="absolute top-4 right-4 bg-[#232629]/80 backdrop-blur-md text-[#eeeef0] px-3 py-1 rounded-full text-xs font-bold flex items-center gap-1">
                    <span className="material-symbols-outlined text-xs">history</span>
                    LAST BOOKED {venue.lastBooked}
                  </div>
                )}
              </div>

              <div className="p-6">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-['Epilogue'] text-xl font-bold leading-none">
                    {venue.name}
                  </h3>
                  <div className="flex items-center gap-1 bg-[#1d2022] px-2 py-1 rounded text-xs font-bold text-[#59f0bb]">
                    <span
                      className="material-symbols-outlined text-[14px]"
                      style={{ fontVariationSettings: "'FILL' 1" }}
                    >
                      star
                    </span>
                    {venue.rating}
                  </div>
                </div>

                <div className="flex items-center gap-4 text-[#aaabad] text-sm mb-6">
                  <span className="flex items-center gap-1">
                    <span className="material-symbols-outlined text-sm">near_me</span>
                    {venue.distance}
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="material-symbols-outlined text-sm">sports_tennis</span>
                    {venue.sports}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <div className="text-[#eeeef0]">
                    <span className="text-lg font-bold">₹{venue.price}</span>
                    <span className="text-xs text-[#aaabad]">/hr</span>
                  </div>
                  <button 
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/venue/${venue.id}`);
                    }}
                    className="bg-[#cafd00] text-[#4a5e00] px-6 py-2 rounded-xl font-bold text-sm active:scale-95 transition-transform"
                  >
                    Book Now
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Bento Grid Info */}
        <div className="grid grid-cols-2 gap-4 mt-6">
          <div className="bg-[#6affc9]/10 border border-[#6affc9]/20 rounded-xl p-5 flex flex-col justify-between aspect-square">
            <span className="material-symbols-outlined text-[#6affc9] text-3xl">groups</span>
            <div>
              <p className="text-[#6affc9] font-['Epilogue'] font-bold text-lg leading-tight">
                Join a<br />Team
              </p>
              <p className="text-[#aaabad] text-xs mt-1">12 games looking for players</p>
            </div>
          </div>

          <div className="bg-[#cafd00]/10 border border-[#cafd00]/20 rounded-xl p-5 flex flex-col justify-between aspect-square">
            <span className="material-symbols-outlined text-[#cafd00] text-3xl">
              workspace_premium
            </span>
            <div>
              <p className="text-[#cafd00] font-['Epilogue'] font-bold text-lg leading-tight">
                Pro<br />Coaching
              </p>
              <p className="text-[#aaabad] text-xs mt-1">Book expert sessions</p>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
