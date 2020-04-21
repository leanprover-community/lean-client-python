lemma zero_max (m : ℕ) : max 0 m = m :=
begin
  apply max_eq_right,
  exact nat.zero_le m,
end

example (m n : ℕ) : m + n = n + m :=
by simp [add_comm]
