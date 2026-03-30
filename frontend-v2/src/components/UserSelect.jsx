import { Users } from "lucide-react";
import { useAppStore } from "../store/useAppStore";

function formatEmployeeId(employeeId) {
  return employeeId?.replace(/^DEMO-/, "") || "N/A";
}

export function UserSelect() {
  const users = useAppStore((state) => state.users);
  const selectedUserId = useAppStore((state) => state.selectedUserId);
  const selectUser = useAppStore((state) => state.selectUser);
  const isLoadingUsers = useAppStore((state) => state.isLoadingUsers);

  return (
    <label className="block rounded-[1.6rem] border border-white/10 bg-white/[0.035] px-3 py-3 text-sm text-slate-300">
      <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-500">
        <Users size={14} className="text-cyan-300/90" />
        Investigation Target
      </div>
      <select
        value={selectedUserId}
        onChange={(event) => selectUser(event.target.value)}
        disabled={isLoadingUsers || users.length === 0}
        className="mt-2.5 w-full rounded-[1.2rem] border border-white/10 bg-slate-950/85 px-4 py-2 pr-11 text-sm font-medium text-white outline-none transition focus:border-cyan-400/40"
      >
        {users.length === 0 ? (
          <option value="">No users loaded</option>
        ) : (
          [<option key="empty-target" value="">Select target</option>].concat(
            users.map((user) => (
              <option key={user.user_id} value={user.user_id}>
                {user.full_name} ({formatEmployeeId(user.employee_id)})
              </option>
            ))
          )
        )}
      </select>
    </label>
  );
}
