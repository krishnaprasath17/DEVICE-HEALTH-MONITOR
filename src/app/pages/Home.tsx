import { useNavigate } from "react-router";

export function Home() {
  const navigate = useNavigate();

  return (
    <main className="pt-24 pb-32 px-6">
      {/* Hero Section */}
      <section className="mb-10">
        <h1 className="font-['Epilogue'] text-5xl font-black tracking-tighter leading-[0.9] text-[#eeeef0] mb-2">
          Ready to play,<br />
          <span className="text-[#cafd00]">Bangalore?</span>
        </h1>
        <p className="text-[#aaabad] font-medium tracking-tight">
          24 courts active in your area right now.
        </p>
      </section>

      {/* Trending Near You */}
      <section className="mb-10">
        <div className="flex items-end justify-between mb-6">
          <h2 className="font-['Epilogue'] text-2xl font-extrabold tracking-tight">
            Trending Near You
          </h2>
          <span className="text-[#cafd00] font-['Inter'] text-sm font-bold uppercase tracking-widest">
            View All
          </span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Badminton Card */}
          <div 
            onClick={() => navigate('/venue/1')}
            className="group relative rounded-xl overflow-hidden aspect-[4/5] bg-[#111416] shadow-2xl cursor-pointer"
          >
            <img
              className="absolute inset-0 w-full h-full object-cover opacity-60 group-hover:scale-105 transition-transform duration-700"
              alt="Indoor badminton court"
              src="https://images.unsplash.com/photo-1626224583764-f87db24ac4ea?w=800&h=1000&fit=crop"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-[#0c0e10] via-[#0c0e10]/20 to-transparent"></div>
            <div className="absolute bottom-0 p-6 w-full">
              <div className="flex gap-2 mb-3">
                <span className="px-3 py-1 bg-[#cafd00] text-[#4a5e00] text-[10px] font-black uppercase tracking-widest rounded-full">
                  Fast Filling
                </span>
                <span className="px-3 py-1 bg-[#232629] text-[#eeeef0] text-[10px] font-bold uppercase tracking-widest rounded-full backdrop-blur-md">
                  Badminton
                </span>
              </div>
              <h3 className="font-['Epilogue'] text-3xl font-extrabold mb-1">
                Playzone Arena
              </h3>
              <p className="text-[#aaabad] text-sm flex items-center gap-1 mb-4">
                <span className="material-symbols-outlined text-xs">schedule</span>
                4:00 PM - 5:00 PM
              </p>
              <button 
                onClick={(e) => {
                  e.stopPropagation();
                  navigate('/venue/1');
                }}
                className="w-full bg-[#cafd00] text-[#4a5e00] py-4 rounded-xl font-bold text-sm active:scale-95 transition-all"
              >
                Book Court
              </button>
            </div>
          </div>

          {/* Swimming Card */}
          <div 
            onClick={() => navigate('/venue/2')}
            className="group relative rounded-xl overflow-hidden aspect-[4/5] bg-[#111416] shadow-2xl cursor-pointer"
          >
            <img
              className="absolute inset-0 w-full h-full object-cover opacity-60 group-hover:scale-105 transition-transform duration-700"
              alt="Modern swimming pool"
              src="https://images.unsplash.com/photo-1576013551627-0cc20b96c2a7?w=800&h=1000&fit=crop"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-[#0c0e10] via-[#0c0e10]/20 to-transparent"></div>
            <div className="absolute bottom-0 p-6 w-full">
              <div className="flex gap-2 mb-3">
                <span className="px-3 py-1 bg-[#6affc9] text-[#006045] text-[10px] font-black uppercase tracking-widest rounded-full">
                  Top Rated
                </span>
                <span className="px-3 py-1 bg-[#232629] text-[#eeeef0] text-[10px] font-bold uppercase tracking-widest rounded-full backdrop-blur-md">
                  Swimming
                </span>
              </div>
              <h3 className="font-['Epilogue'] text-3xl font-extrabold mb-1">Aqua Center</h3>
              <p className="text-[#aaabad] text-sm flex items-center gap-1 mb-4">
                <span className="material-symbols-outlined text-xs">schedule</span>
                Open until 10:00 PM
              </p>
              <button 
                onClick={(e) => {
                  e.stopPropagation();
                  navigate('/venue/2');
                }}
                className="w-full bg-[#cafd00] text-[#4a5e00] py-4 rounded-xl font-bold text-sm active:scale-95 transition-all"
              >
                Join Session
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Local Groups */}
      <section className="mb-10">
        <div className="flex items-end justify-between mb-6">
          <h2 className="font-['Epilogue'] text-2xl font-extrabold tracking-tight">
            Local Groups
          </h2>
          <span className="text-[#6affc9] font-['Inter'] text-sm font-bold uppercase tracking-widest">
            Meet Pros
          </span>
        </div>
        <div className="space-y-3">
          <div className="bg-[#111416] p-4 rounded-xl flex items-center justify-between border border-[#46484a]/10">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-xl bg-[#6affc9]/20 flex items-center justify-center text-[#6affc9]">
                <span className="material-symbols-outlined text-3xl">sports_soccer</span>
              </div>
              <div>
                <h4 className="font-bold text-lg leading-tight">HSR Footballers</h4>
                <p className="text-[#aaabad] text-xs font-medium uppercase tracking-tighter">
                  142 Players • 3 Games Today
                </p>
              </div>
            </div>
            <button className="w-10 h-10 rounded-full bg-[#1d2022] flex items-center justify-center text-[#eeeef0] active:scale-90 duration-200">
              <span className="material-symbols-outlined">chevron_right</span>
            </button>
          </div>

          <div className="bg-[#111416] p-4 rounded-xl flex items-center justify-between border border-[#46484a]/10">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-xl bg-[#6affc9]/20 flex items-center justify-center text-[#6affc9]">
                <span className="material-symbols-outlined text-3xl">directions_run</span>
              </div>
              <div>
                <h4 className="font-bold text-lg leading-tight">Koramangala Runners</h4>
                <p className="text-[#aaabad] text-xs font-medium uppercase tracking-tighter">
                  88 Active • Morning Sprints
                </p>
              </div>
            </div>
            <button className="w-10 h-10 rounded-full bg-[#1d2022] flex items-center justify-center text-[#eeeef0] active:scale-90 duration-200">
              <span className="material-symbols-outlined">chevron_right</span>
            </button>
          </div>
        </div>
      </section>

      {/* Beginner Friendly */}
      <section className="mb-4">
        <h2 className="font-['Epilogue'] text-2xl font-extrabold tracking-tight mb-6">
          Beginner Friendly
        </h2>
        <div className="flex gap-4 overflow-x-auto pb-4 -mx-6 px-6 scrollbar-hide">
          {[
            {
              title: "Intro to Yoga",
              venue: "Soul Space Indiranagar",
              img: "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=400&h=400&fit=crop",
            },
            {
              title: "Ping Pong Basics",
              venue: "Urban Club HSR",
              img: "https://images.unsplash.com/photo-1534158914592-062992fbe900?w=400&h=400&fit=crop",
            },
            {
              title: "Strength 101",
              venue: "The Tribe Gym",
              img: "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=400&h=400&fit=crop",
            },
          ].map((item, idx) => (
            <div key={idx} className="flex-none w-48 group">
              <div className="relative w-full aspect-square rounded-2xl overflow-hidden mb-3">
                <img
                  className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500"
                  alt={item.title}
                  src={item.img}
                />
                <div className="absolute inset-0 bg-[#cafd00]/5"></div>
              </div>
              <h5 className="font-bold text-sm mb-1">{item.title}</h5>
              <p className="text-xs text-[#aaabad] font-medium">{item.venue}</p>
            </div>
          ))}
        </div>
      </section>

      {/* FAB */}
      <button className="fixed bottom-24 right-6 w-14 h-14 bg-[#cafd00] text-[#4a5e00] rounded-full shadow-2xl flex items-center justify-center z-40 active:scale-90 transition-transform">
        <span
          className="material-symbols-outlined text-3xl"
          style={{ fontVariationSettings: "'FILL' 1" }}
        >
          add
        </span>
      </button>
    </main>
  );
}
