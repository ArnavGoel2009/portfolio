import unittest,random
from optimizer import *
class T(unittest.TestCase):
 def test_kerf(self): self.assertEqual(used_length([1000,1000,1000],3),3006)
 def test_boundary(self):
  b=best_fit_decreasing([Piece('a',3000),Piece('b',2997)],6000,3);self.assertEqual(len(b),1);self.assertEqual(summarize(b,6000,3)['waste_mm'],0)
 def test_impossible(self):
  with self.assertRaises(ValueError): best_fit_decreasing([Piece('x',6001)],6000,3)
 def test_exact_not_worse(self):
  ps=[Piece(str(i),x) for i,x in enumerate([3300,2700,3000,2997,2000,1997,1997])];self.assertLessEqual(len(exact_branch_and_bound(ps,6000,3)),len(best_fit_decreasing(ps,6000,3)))
 def test_ids(self):
  ps=[Piece(str(i),1000+i*10) for i in range(8)];b=best_fit_decreasing(ps,6000,3);self.assertEqual(sorted(p.id for bar in b for p in bar),sorted(p.id for p in ps))
 def test_profiles(self): self.assertEqual(set(optimize_by_profile([Piece('a',3000,'A'),Piece('b',3000,'B')])),{'A','B'})
 def test_random_no_overfill(self):
  random.seed(7);ps=[Piece(str(i),random.randint(250,3000)) for i in range(100)]
  for alg in (first_fit_decreasing,best_fit_decreasing): self.assertTrue(all(used_length([p.length_mm for p in b],3)<=6000 for b in alg(ps,6000,3)))
if __name__=='__main__': unittest.main()
