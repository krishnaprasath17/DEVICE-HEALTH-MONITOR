import { useParams } from "react-router";
import { useState } from "react";

export function VenueDetail() {
  const { id } = useParams();
  const [selectedSlot, setSelectedSlot] = useState("06:00 AM");

  const venues = {
    "1": {
      name: "INDIRANAGAR\nSPORTS CLUB",
      sport: "Badminton",
      image: "https://images.unsplash.com/photo-1626224583764-f87db24ac4ea?w=1200&h=800&fit=crop",
      rating: 4.8,
      reviews: "120+",
      distance: "0.8 km",
      description: "Premium urban sports facility in the heart of Indiranagar. Featuring 6 international-standard synthetic badminton courts, professional lighting, and state-of-the-art amenities for the elite athlete.",
      price: 450,
    },
    "2": {
      name: "AQUA\nCENTER",
      sport: "Swimming",
      image: "https://images.unsplash.com/photo-1576013551627-0cc20b96c2a7?w=1200&h=800&fit=crop",
      rating: 4.9,
      reviews: "85+",
      distance: "1.2 km",
      description: "Olympic-sized swimming pool with professional coaching staff. Climate controlled facility with separate lanes for training and leisure swimming.",
      price: 350,
    },
  };

  const venue = venues[id as keyof typeof venues] || venues["1"];

  const amenities = [
    { icon: "ac_unit", label: "Fully AC" },
    { icon: "shower", label: "Showers" },
    { icon: "local_parking", label: "Parking" },
    { icon: "water_drop", label: "Water" },
  ];

  const slots = [
    { time: "06:00 AM", price: 450, available: true },
    { time: "07:00 AM", price: 450, available: false },
    { time: "08:00 AM", price: 450, available: false },
    { time: "04:00 PM", price: 600, available: true },
    { time: "05:00 PM", price: 600, available: true },
    { time: "06:00 PM", price: 750, available: true },
  ];

  const coaches = [
    {
      name: "Coach Rohan",
      specialty: "Badminton Pro",
      image: "https://images.unsplash.com/photo-1568602471122-7832951cc4c5?w=200&h=200&fit=crop",
      experience: "8+",
    },
    {
      name: "Coach Sarah",
      specialty: "Fitness Lead",
      image: "https://images.unsplash.com/photo-1594744803329-e58b31de8bf5?w=200&h=200&fit=crop",
      experience: "12+",
    },
  ];

  return (
    <main className="pb-32">
      {/* Hero Section */}
      <section className="relative h-[397px] w-full overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-t from-[#0c0e10] via-transparent to-transparent z-10"></div>
        <div className="absolute inset-0 bg-[#cafd00]/5 z-10"></div>
        <img
          alt={venue.name}
          className="w-full h-full object-cover"
          src={venue.image}
        />
        <div className="absolute bottom-0 left-0 p-6 z-20 w-full">
          <div className="flex flex-wrap gap-2 mb-3">
            <span className="px-3 py-1 rounded-md bg-[#6affc9] text-[#006045] text-[10px] font-bold tracking-widest uppercase">
              {venue.sport}
            </span>
            <span className="px-3 py-1 rounded-md bg-[#232629] text-[#cafd00] text-[10px] font-bold tracking-widest uppercase">
              Open Now
            </span>
          </div>
          <h1 className="font-['Epilogue'] text-4xl md:text-5xl font-black tracking-tighter text-[#cafd00] leading-none mb-2 whitespace-pre-line">
            {venue.name}
          </h1>
          <div className="flex items-center gap-4 text-[#aaabad] text-sm">
            <div className="flex items-center gap-1">
              <span
                className="material-symbols-outlined text-xs"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                star
              </span>
              <span className="font-bold text-[#eeeef0]">{venue.rating}</span>
              <span>({venue.reviews} reviews)</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="material-symbols-outlined text-xs">distance</span>
              <span>{venue.distance}</span>
            </div>
          </div>
        </div>
      </section>

      {/* About Section */}
      <section className="px-6 mt-8">
        <h2 className="font-['Epilogue'] text-xl font-extrabold tracking-tight mb-4">
          ABOUT THE VENUE
        </h2>
        <p className="text-[#aaabad] leading-relaxed text-sm mb-6">
          {venue.description}
        </p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {amenities.map((amenity, idx) => (
            <div
              key={idx}
              className="flex items-center gap-3 p-3 rounded-xl bg-[#111416]"
            >
              <span className="material-symbols-outlined text-[#ccffe6]">{amenity.icon}</span>
              <span className="text-xs font-medium">{amenity.label}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Available Slots */}
      <section className="mt-10 px-6">
        <div className="flex justify-between items-end mb-6">
          <div>
            <h2 className="font-['Epilogue'] text-xl font-extrabold tracking-tight">
              AVAILABLE SLOTS
            </h2>
            <p className="text-[10px] text-[#cafd00] uppercase font-bold tracking-[0.2em] mt-1">
              Today, 24 Oct
            </p>
          </div>
          <button className="text-xs font-bold text-[#aaabad] underline">
            View Calendar
          </button>
        </div>
        <div className="grid grid-cols-3 gap-3">
          {slots.map((slot, idx) => (
            <button
              key={idx}
              disabled={!slot.available}
              onClick={() => slot.available && setSelectedSlot(slot.time)}
              className={`p-4 rounded-xl text-center transition-all ${
                !slot.available
                  ? "bg-[#111416] opacity-50 cursor-not-allowed"
                  : selectedSlot === slot.time
                  ? "bg-[#1d2022] border-2 border-[#cafd00] active:scale-95"
                  : "bg-[#1d2022] border border-[#46484a]/20 active:scale-95"
              }`}
            >
              <p className={`text-[10px] font-bold mb-1 ${
                !slot.available ? "text-[#aaabad]" : selectedSlot === slot.time ? "text-[#cafd00]" : "text-[#aaabad]"
              }`}>
                {slot.time}
              </p>
              <p className="text-xs font-bold">
                {slot.available ? `₹${slot.price}` : "BOOKED"}
              </p>
            </button>
          ))}
        </div>
      </section>

      {/* Coach Profiles */}
      <section className="mt-12 px-6">
        <h2 className="font-['Epilogue'] text-xl font-extrabold tracking-tight mb-6">
          COACH PROFILES
        </h2>
        <div className="flex gap-4 overflow-x-auto scrollbar-hide pb-4 -mx-6 px-6">
          {coaches.map((coach, idx) => (
            <div
              key={idx}
              className="flex-none w-64 bg-[#111416] rounded-2xl overflow-hidden p-4 group"
            >
              <div className="flex items-center gap-4 mb-4">
                <div className="w-16 h-16 rounded-xl overflow-hidden bg-[#1d2022]">
                  <img
                    alt={coach.name}
                    className="w-full h-full object-cover"
                    src={coach.image}
                  />
                </div>
                <div>
                  <h3 className="font-bold text-[#eeeef0]">{coach.name}</h3>
                  <p className="text-[10px] text-[#6affc9] font-bold tracking-widest uppercase">
                    {coach.specialty}
                  </p>
                </div>
              </div>
              <div className="flex justify-between items-center">
                <div className="flex -space-x-2">
                  <div className="w-6 h-6 rounded-full border-2 border-[#111416] bg-[#1d2022] flex items-center justify-center text-[8px] font-bold">
                    {coach.experience}
                  </div>
                  <div className="w-6 h-6 rounded-full border-2 border-[#111416] bg-[#cafd00] text-[#4a5e00] flex items-center justify-center">
                    <span
                      className="material-symbols-outlined text-[10px]"
                    >
                      verified
                    </span>
                  </div>
                </div>
                <button className="text-xs font-bold text-[#cafd00] px-4 py-1.5 rounded-lg border border-[#cafd00]/30">
                  Book Session
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Upcoming Events */}
      <section className="mt-8 px-6">
        <h2 className="font-['Epilogue'] text-xl font-extrabold tracking-tight mb-6">
          UPCOMING EVENTS
        </h2>
        <div className="space-y-4">
          <div className="relative bg-[#1d2022] rounded-2xl overflow-hidden flex h-32">
            <div className="w-1/3 h-full">
              <img
                alt="Weekend event"
                className="w-full h-full object-cover"
                src="https://images.unsplash.com/photo-1554068865-24cecd4e34b8?w=400&h=400&fit=crop"
              />
            </div>
            <div className="p-4 flex-1 flex flex-col justify-center">
              <div className="text-[9px] font-black text-[#6affc9] tracking-widest uppercase mb-1">
                COMMUNITY TOURNAMENT
              </div>
              <h3 className="font-['Epilogue'] text-lg font-bold leading-tight">
                WEEKEND SMASH VOL. 4
              </h3>
              <p className="text-[10px] text-[#aaabad] mt-1 flex items-center gap-1">
                <span className="material-symbols-outlined text-xs">event</span>
                28 Oct • 09:00 AM
              </p>
            </div>
          </div>

          <div className="relative bg-[#111416] rounded-2xl p-6 border-l-4 border-[#cafd00]">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="font-['Epilogue'] text-lg font-bold leading-tight">
                  Advanced Drill Night
                </h3>
                <p className="text-xs text-[#aaabad] mt-1">
                  High intensity shuttle drills for intermediate players.
                </p>
              </div>
              <div className="text-right">
                <span className="text-[#cafd00] font-black text-xl leading-none">FREE</span>
                <p className="text-[8px] font-bold text-[#aaabad]">COMMUNITY</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Fixed Bottom Book Button */}
      <div className="fixed bottom-24 left-0 w-full px-6 z-40 md:hidden">
        <button className="w-full py-5 bg-[#cafd00] text-[#4a5e00] rounded-xl font-['Epilogue'] font-black text-lg tracking-tight shadow-xl active:scale-[0.98] transition-all">
          BOOK NOW • ₹{venue.price}
        </button>
      </div>
    </main>
  );
}
