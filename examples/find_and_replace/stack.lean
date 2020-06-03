structure stack (α : Type) :=
(inner_list : list α)

namespace stack

def pop {α : Type} [h : inhabited α] (s : stack α) : α × stack α :=
match s.inner_list with
| a :: as := (a, { stack. inner_list := as })
| [] := (h.default, { stack. inner_list := []})
end

def push {α : Type} (s : stack α) (a : α) : stack α :=
{ stack. inner_list := a :: s.inner_list }

-- should be peek, we will change it later
def head {α : Type} [inhabited α] (s : stack α) : α := s.inner_list.head

lemma head_push (α : Type) [inhabited α] (s : stack α) (a : α) : (s.push a).head = a := begin
rw [stack.head, stack.push],
unfold_projs,
rw [list.head]
end

lemma pop_head (α : Type) [inhabited α] (s : stack α) (a : α) : s.pop.fst = s.head := begin
rw [stack.pop, stack.head],
induction s.inner_list,
{simp [stack.pop._match_1]},
rw [list.head],
simp [stack.pop._match_1]
end

end stack