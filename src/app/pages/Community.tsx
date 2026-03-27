export function Community() {
  const pickupGames = [
    {
      title: "5v5 Football at Turfpark",
      sport: "Football",
      time: "Today • 18:00",
      spotsLeft: 4,
      level: "Competitive level",
      bgColor: "bg-[#1d2022]",
      borderColor: "border-[#cafd00]",
    },
    {
      title: "3v3 Hoops",
      sport: "Basketball",
      time: "Tomorrow • 07:30",
      icon: "sports_basketball",
      iconColor: "text-[#59f0bb]",
    },
    {
      title: "Mixed Padel",
      sport: "Tennis",
      time: "Sat • 16:00",
      icon: "sports_tennis",
      iconColor: "text-[#e5e2e1]",
    },
  ];

  const clubs = [
    {
      name: "Red Devils FC",
      members: "840 Active Members",
      level: "Semi-pro",
      image: "https://images.unsplash.com/photo-1579952363873-27f3bade9f55?w=600&h=400&fit=crop",
    },
    {
      name: "Bangalore Brevet",
      members: "1.2k Active Members",
      level: "All Levels",
      image: "https://images.unsplash.com/photo-1541625602330-2277a4c46182?w=600&h=400&fit=crop",
    },
  ];

  return (
    <main className="pt-20 pb-28 min-h-screen bg-[#0c0e10]" style={{
      backgroundImage: "radial-gradient(circle at 2px 2px, rgba(202, 253, 0, 0.05) 1px, transparent 0)",
      backgroundSize: "24px 24px"
    }}>
      {/* Hero Section */}
      <section className="px-6 mb-10">
        <div className="relative overflow-hidden rounded-xl bg-[#111416] p-8 border border-[#46484a]/10">
          <div className="relative z-10">
            <span className="text-[#59f0bb] font-['Inter'] text-xs uppercase tracking-[0.2em] mb-2 block">
              Community Hub
            </span>
            <h1 className="font-['Epilogue'] text-5xl font-black tracking-tighter text-[#eeeef0] leading-none mb-4">
              The Locker <br />
              <span className="text-[#cafd00]">Room</span>
            </h1>
            <div className="flex items-center gap-3">
              <div className="flex -space-x-3">
                {[
                  "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop",
                  "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=100&h=100&fit=crop",
                  "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=100&h=100&fit=crop",
                ].map((src, idx) => (
                  <img
                    key={idx}
                    className="w-8 h-8 rounded-full border-2 border-[#111416]"
                    alt="User avatar"
                    src={src}
                  />
                ))}
              </div>
              <p className="text-[#aaabad] text-sm font-medium">124 Members Online</p>
            </div>
          </div>
          <div className="absolute -right-10 -bottom-10 w-48 h-48 bg-[#cafd00]/10 rounded-full blur-3xl"></div>
        </div>
      </section>

      {/* Pick-up Games */}
      <section className="px-6 mb-10">
        <div className="flex justify-between items-end mb-6">
          <div>
            <h2 className="font-['Epilogue'] text-2xl font-bold">Pick-up Games</h2>
            <p className="text-[#aaabad] text-sm">Jump into the action near you</p>
          </div>
          <button className="text-[#cafd00] font-['Inter'] text-sm font-semibold hover:underline">
            View All
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Large Card */}
          <div className={`${pickupGames[0].bgColor} rounded-xl p-6 flex flex-col justify-between border-l-4 ${pickupGames[0].borderColor} shadow-lg`}>
            <div>
              <div className="flex justify-between items-start mb-4">
                <span className="bg-[#cafd00]/10 text-[#cafd00] px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider">
                  {pickupGames[0].sport}
                </span>
                <span className="text-[#aaabad] text-xs">{pickupGames[0].time}</span>
              </div>
              <h3 className="font-['Epilogue'] text-xl font-extrabold mb-1">
                {pickupGames[0].title}
              </h3>
              <p className="text-[#aaabad] text-sm mb-6">
                {pickupGames[0].spotsLeft} spots left • {pickupGames[0].level}
              </p>
            </div>
            <button className="bg-[#cafd00] text-[#4a5e00] w-full py-3 rounded-xl font-bold active:scale-[0.98] transition-all">
              Join Game
            </button>
          </div>

          <div className="grid grid-rows-2 gap-4">
            {pickupGames.slice(1).map((game, idx) => (
              <div
                key={idx}
                className="bg-[#171a1c] p-4 rounded-xl flex items-center justify-between border border-[#46484a]/20"
              >
                <div className="flex gap-4 items-center">
                  <div className="w-12 h-12 bg-[#6affc9]/10 rounded-lg flex items-center justify-center">
                    <span className={`material-symbols-outlined ${game.iconColor}`}>
                      {game.icon}
                    </span>
                  </div>
                  <div>
                    <h4 className="font-bold text-sm">{game.title}</h4>
                    <p className="text-[#aaabad] text-xs">{game.time}</p>
                  </div>
                </div>
                <button className="bg-[#232629] text-[#cafd00] px-4 py-2 rounded-lg text-xs font-bold uppercase active:scale-95 transition-all">
                  Join
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Local Clubs */}
      <section className="mb-10">
        <div className="px-6 flex justify-between items-end mb-6">
          <div>
            <h2 className="font-['Epilogue'] text-2xl font-bold">Local Clubs</h2>
            <p className="text-[#aaabad] text-sm">Elite communities in Indiranagar</p>
          </div>
        </div>

        <div className="flex overflow-x-auto gap-6 px-6 scrollbar-hide">
          {clubs.map((club, idx) => (
            <div
              key={idx}
              className="min-w-[280px] bg-[#111416] rounded-xl overflow-hidden border border-[#46484a]/10"
            >
              <div
                className="h-32 bg-cover bg-center relative"
                style={{ backgroundImage: `url(${club.image})` }}
              >
                <div className="absolute inset-0 bg-gradient-to-t from-[#111416] to-transparent"></div>
              </div>
              <div className="p-5">
                <h4 className="font-['Epilogue'] text-lg font-bold mb-1">{club.name}</h4>
                <p className="text-[#aaabad] text-xs mb-4">
                  {club.members} • {club.level}
                </p>
                <button className="w-full bg-[#6affc9] text-[#006045] py-2 rounded-lg text-sm font-bold active:scale-95 transition-all">
                  Request to Join
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Community Feed */}
      <section className="px-6 mb-10">
        <h2 className="font-['Epilogue'] text-2xl font-bold mb-6">What's Happening</h2>
        <div className="space-y-4">
          <div className="bg-[#171a1c] p-5 rounded-xl border border-[#46484a]/10">
            <div className="flex items-center gap-3 mb-4">
              <img
                className="w-10 h-10 rounded-full"
                alt="User"
                src="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=100&h=100&fit=crop"
              />
              <div>
                <h5 className="text-sm font-bold">Rahul Sharma</h5>
                <p className="text-[10px] text-[#aaabad]">
                  2h ago in <span className="text-[#ccffe6]">Cricket Connect</span>
                </p>
              </div>
            </div>
            <p className="text-sm text-[#eeeef0] leading-relaxed mb-4">
              Great match today guys! Does anyone have the highlights recorded from the second
              half? Looking to improve my bowling stance.
            </p>
            <div className="flex gap-4">
              <div className="flex items-center gap-1 text-[#aaabad]">
                <span className="material-symbols-outlined text-sm">thumb_up</span>
                <span className="text-xs">24</span>
              </div>
              <div className="flex items-center gap-1 text-[#aaabad]">
                <span className="material-symbols-outlined text-sm">chat_bubble</span>
                <span className="text-xs">12</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Host a Game FAB */}
      <button className="fixed right-6 bottom-28 z-50 bg-[#cafd00] text-[#4a5e00] px-6 py-4 rounded-full shadow-2xl flex items-center gap-3 active:scale-90 duration-200">
        <span
          className="material-symbols-outlined"
          style={{ fontVariationSettings: "'FILL' 1" }}
        >
          add
        </span>
        <span className="font-bold text-sm">Host a Game</span>
      </button>
    </main>
  );
}
