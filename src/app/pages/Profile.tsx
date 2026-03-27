export function Profile() {
  const stats = [
    { label: "Games Played", value: "24", icon: "sports_score" },
    { label: "Hours Active", value: "48", icon: "schedule" },
    { label: "Communities", value: "3", icon: "groups" },
  ];

  const sports = [
    { name: "Badminton", level: "Intermediate", icon: "sports_tennis", color: "#cafd00" },
    { name: "Football", level: "Beginner", icon: "sports_soccer", color: "#6affc9" },
  ];

  return (
    <main className="pt-20 pb-28 px-6 min-h-screen">
      {/* Profile Header */}
      <section className="mb-10">
        <div className="flex items-center gap-4 mb-6">
          <div className="w-24 h-24 rounded-full bg-[#1d2022] border-2 border-[#cafd00] overflow-hidden">
            <img
              className="w-full h-full object-cover"
              alt="Profile"
              src="https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=200&h=200&fit=crop"
            />
          </div>
          <div className="flex-1">
            <h1 className="font-['Epilogue'] text-3xl font-black tracking-tight mb-1">
              Alex Kumar
            </h1>
            <p className="text-[#aaabad] text-sm mb-2">Indiranagar, Bangalore</p>
            <button className="bg-[#1d2022] text-[#cafd00] px-4 py-2 rounded-lg text-sm font-bold">
              Edit Profile
            </button>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-3">
          {stats.map((stat, idx) => (
            <div key={idx} className="bg-[#111416] rounded-xl p-4 text-center">
              <span className="material-symbols-outlined text-[#cafd00] text-2xl mb-2 block">
                {stat.icon}
              </span>
              <p className="font-['Epilogue'] font-black text-2xl mb-1">{stat.value}</p>
              <p className="text-[10px] text-[#aaabad] uppercase tracking-wide">{stat.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* My Sports */}
      <section className="mb-10">
        <h2 className="font-['Epilogue'] text-xl font-bold mb-4">My Sports</h2>
        <div className="space-y-3">
          {sports.map((sport, idx) => (
            <div
              key={idx}
              className="bg-[#111416] p-4 rounded-xl flex items-center justify-between border border-[#46484a]/10"
            >
              <div className="flex items-center gap-4">
                <div
                  className="w-12 h-12 rounded-xl flex items-center justify-center"
                  style={{ backgroundColor: `${sport.color}20` }}
                >
                  <span
                    className="material-symbols-outlined text-2xl"
                    style={{ color: sport.color }}
                  >
                    {sport.icon}
                  </span>
                </div>
                <div>
                  <h3 className="font-bold text-sm">{sport.name}</h3>
                  <p className="text-xs text-[#aaabad]">{sport.level}</p>
                </div>
              </div>
              <button className="w-8 h-8 rounded-full bg-[#1d2022] flex items-center justify-center">
                <span className="material-symbols-outlined text-sm">chevron_right</span>
              </button>
            </div>
          ))}
          <button className="w-full bg-[#1d2022] p-4 rounded-xl flex items-center justify-center gap-2 text-[#cafd00] font-bold text-sm active:scale-95 transition-all border border-[#46484a]/10">
            <span className="material-symbols-outlined">add</span>
            Add Sport
          </button>
        </div>
      </section>

      {/* Quick Actions */}
      <section className="mb-10">
        <h2 className="font-['Epilogue'] text-xl font-bold mb-4">Quick Actions</h2>
        <div className="grid grid-cols-2 gap-3">
          <button className="bg-[#111416] p-6 rounded-xl text-left active:scale-95 transition-all">
            <span className="material-symbols-outlined text-[#6affc9] text-3xl mb-2 block">
              history
            </span>
            <h3 className="font-bold text-sm mb-1">Activity History</h3>
            <p className="text-xs text-[#aaabad]">View all sessions</p>
          </button>
          <button className="bg-[#111416] p-6 rounded-xl text-left active:scale-95 transition-all">
            <span className="material-symbols-outlined text-[#cafd00] text-3xl mb-2 block">
              workspace_premium
            </span>
            <h3 className="font-bold text-sm mb-1">Go Premium</h3>
            <p className="text-xs text-[#aaabad]">Unlock features</p>
          </button>
        </div>
      </section>

      {/* Settings */}
      <section>
        <h2 className="font-['Epilogue'] text-xl font-bold mb-4">Settings</h2>
        <div className="space-y-2">
          {[
            { label: "Notifications", icon: "notifications" },
            { label: "Privacy", icon: "lock" },
            { label: "Payment Methods", icon: "credit_card" },
            { label: "Help & Support", icon: "help" },
          ].map((item, idx) => (
            <button
              key={idx}
              className="w-full bg-[#111416] p-4 rounded-xl flex items-center justify-between active:scale-95 transition-all"
            >
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined text-[#aaabad]">{item.icon}</span>
                <span className="text-sm font-medium">{item.label}</span>
              </div>
              <span className="material-symbols-outlined text-[#aaabad]">chevron_right</span>
            </button>
          ))}
        </div>
      </section>
    </main>
  );
}
