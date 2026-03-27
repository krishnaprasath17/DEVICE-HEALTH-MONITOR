export function Bookings() {
  const upcomingBookings = [
    {
      venue: "Indiranagar Sports Club",
      sport: "Badminton",
      date: "Tomorrow",
      time: "06:00 AM - 07:00 AM",
      court: "Court 3",
      price: 450,
      image: "https://images.unsplash.com/photo-1626224583764-f87db24ac4ea?w=400&h=300&fit=crop",
    },
    {
      venue: "The Arena Rooftop Turf",
      sport: "Football",
      date: "Oct 25",
      time: "06:00 PM - 07:00 PM",
      court: "Main Turf",
      price: 1200,
      image: "https://images.unsplash.com/photo-1575361204480-aadea25e6e68?w=400&h=300&fit=crop",
    },
  ];

  const pastBookings = [
    {
      venue: "Aqua Center",
      sport: "Swimming",
      date: "Oct 18",
      time: "07:00 AM - 08:00 AM",
      status: "Completed",
    },
  ];

  return (
    <main className="pt-20 pb-28 px-6 min-h-screen">
      <section className="mb-10">
        <h1 className="font-['Epilogue'] text-4xl font-black tracking-tighter leading-[0.9] text-[#eeeef0] mb-2">
          Your <span className="text-[#cafd00]">Bookings</span>
        </h1>
        <p className="text-[#aaabad] font-medium">Manage your upcoming sessions</p>
      </section>

      {/* Upcoming Bookings */}
      <section className="mb-10">
        <h2 className="font-['Epilogue'] text-xl font-bold mb-4">Upcoming</h2>
        <div className="space-y-4">
          {upcomingBookings.map((booking, idx) => (
            <div
              key={idx}
              className="bg-[#111416] rounded-xl overflow-hidden border border-[#46484a]/10"
            >
              <div className="flex gap-4">
                <div className="w-32 h-32 flex-shrink-0">
                  <img
                    className="w-full h-full object-cover"
                    alt={booking.venue}
                    src={booking.image}
                  />
                </div>
                <div className="flex-1 py-4 pr-4">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <span className="px-2 py-1 bg-[#cafd00]/10 text-[#cafd00] rounded text-[10px] font-bold uppercase">
                        {booking.sport}
                      </span>
                    </div>
                    <button className="text-[#aaabad] hover:text-[#eeeef0]">
                      <span className="material-symbols-outlined text-xl">more_vert</span>
                    </button>
                  </div>
                  <h3 className="font-bold text-sm mb-1">{booking.venue}</h3>
                  <p className="text-xs text-[#aaabad] mb-2">
                    {booking.date} • {booking.time}
                  </p>
                  <p className="text-xs text-[#aaabad] mb-3">{booking.court}</p>
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-sm">₹{booking.price}</span>
                    <button className="bg-[#1d2022] text-[#cafd00] px-4 py-1.5 rounded-lg text-xs font-bold">
                      View Details
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Past Bookings */}
      <section>
        <h2 className="font-['Epilogue'] text-xl font-bold mb-4">Past Bookings</h2>
        <div className="space-y-3">
          {pastBookings.map((booking, idx) => (
            <div
              key={idx}
              className="bg-[#111416] rounded-xl p-4 border border-[#46484a]/10 opacity-60"
            >
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-bold text-sm mb-1">{booking.venue}</h3>
                  <p className="text-xs text-[#aaabad]">
                    {booking.date} • {booking.time}
                  </p>
                </div>
                <span className="px-2 py-1 bg-[#6affc9]/10 text-[#6affc9] rounded text-[10px] font-bold uppercase">
                  {booking.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Empty State Hint */}
      <div className="mt-10 bg-[#1d2022] rounded-xl p-8 text-center border border-[#46484a]/10">
        <span className="material-symbols-outlined text-[#cafd00] text-5xl mb-4 block">
          event_available
        </span>
        <h3 className="font-['Epilogue'] font-bold text-lg mb-2">
          Book Your Next Session
        </h3>
        <p className="text-sm text-[#aaabad] mb-4">
          Discover venues and activities near you
        </p>
        <button className="bg-[#cafd00] text-[#4a5e00] px-6 py-3 rounded-xl font-bold text-sm active:scale-95 transition-transform">
          Explore Venues
        </button>
      </div>
    </main>
  );
}
