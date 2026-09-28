"""

Hash table with chaining, random hashing, and resizing.

For encoded keys that differ modulo P, the random hash gives a collision
chance of at most 1/m. A new hash is chosen when the table resizes.

Run: python hash_table.py

"""



import random

import sys

import time



# Prime used by the hash function.

P = (1 << 61) - 1





class HashTable:

    """Hash table with chaining. Supports insert, search, and delete.

    Each bucket stores (key, value) pairs. The table grows when it gets too
    full and shrinks when it gets too empty.

    """



    def __init__(self, initial_capacity=8, max_load=0.75, min_load=0.25,

                 auto_resize=True, seed=None):

        if initial_capacity < 1:

            raise ValueError("initial_capacity must be positive")

        if not 0 < min_load < max_load:

            raise ValueError("require 0 < min_load < max_load")



        self._m = 1

        while self._m < initial_capacity:

            self._m *= 2              # keep capacity a power of two

        self._initial_m = self._m

        self._n = 0

        self._buckets = [[] for _ in range(self._m)]



        self.max_load = max_load

        self.min_load = min_load

        self.auto_resize = auto_resize



        self._rng = random.Random(seed)

        self._draw_hash()



        # Measurements for the experiments.

        self.probes = 0       # key comparisons

        self.collisions = 0   # new keys added to nonempty buckets

        self.resizes = 0

        self.rehash_moves = 0 # entries moved during resizing



    # ---------------- hashing ----------------



    def _draw_hash(self):

        """Choose new random hash parameters."""

        self._a = self._rng.randrange(1, P)

        self._b = self._rng.randrange(0, P)



    @staticmethod

    def _to_int(key):

        """Turn a hashable key into a non-negative integer.

        Non-negative integers are used directly. Negative integers are
        transformed. Other keys use Python's hash(). Different keys can
        produce the same number, so the hash guarantee only applies when
        their resulting values differ modulo P.

        """

        if isinstance(key, int) and not isinstance(key, bool):

            return key if key >= 0 else ~key * 2 + 1

        return hash(key) & sys.maxsize



    def _hash(self, key):

        return ((self._a * self._to_int(key) + self._b) % P) % self._m



    # ---------------- core operations ----------------



    def insert(self, key, value):

        """Add a new key or update an existing one. Expected O(1 + alpha)."""

        i = self._hash(key)

        bucket = self._buckets[i]



        # Update the key if it already exists.

        for idx, (k, _) in enumerate(bucket):

            self.probes += 1

            if k == key:

                bucket[idx] = (key, value)

                return



        if bucket:

            self.collisions += 1

        bucket.append((key, value))

        self._n += 1



        if self.auto_resize and self.load_factor > self.max_load:

            self._resize(self._m * 2)



    def search(self, key, default=None):

        """Return the value for key, or default if it is missing."""

        for k, v in self._buckets[self._hash(key)]:

            self.probes += 1

            if k == key:

                return v

        return default



    def delete(self, key):

        """Remove key and return its value. Raise KeyError if it is missing."""

        i = self._hash(key)

        bucket = self._buckets[i]



        for idx, (k, v) in enumerate(bucket):

            self.probes += 1

            if k == key:

                # Replace this entry with the last one, then remove the last.

                # This avoids shifting the other entries.

                bucket[idx] = bucket[-1]

                bucket.pop()

                self._n -= 1



                if (self.auto_resize and self._m > self._initial_m

                        and self.load_factor < self.min_load):

                    self._resize(max(self._initial_m, self._m // 2))

                return v



        raise KeyError(key)



    # ---------------- resizing ----------------



    def _resize(self, new_m):

        """Build a new table with a new hash and the requested capacity."""

        old = self._buckets

        self._m = new_m

        self._buckets = [[] for _ in range(new_m)]

        self._draw_hash()          # choose a new hash

        self.resizes += 1



        for bucket in old:

            for k, v in bucket:

                self._buckets[self._hash(k)].append((k, v))

                self.rehash_moves += 1



    # ---------------- conveniences ----------------



    @property

    def load_factor(self):

        return self._n / self._m



    @property

    def capacity(self):

        return self._m



    def __len__(self):

        return self._n



    def __contains__(self, key):

        sentinel = object()

        return self.search(key, sentinel) is not sentinel



    def __setitem__(self, key, value):

        self.insert(key, value)



    def __getitem__(self, key):

        sentinel = object()

        v = self.search(key, sentinel)

        if v is sentinel:

            raise KeyError(key)

        return v



    def __delitem__(self, key):

        self.delete(key)



    def items(self):

        for bucket in self._buckets:

            for pair in bucket:

                yield pair



    def chain_lengths(self):

        return [len(b) for b in self._buckets]



    def stats(self):

        lengths = self.chain_lengths()

        return {

            "n": self._n, "m": self._m,

            "load_factor": self.load_factor,

            "empty_slots": lengths.count(0),

            "max_chain": max(lengths) if lengths else 0,

            "collisions": self.collisions,

            "resizes": self.resizes,

        }





class BadHashTable(HashTable):

    """A fixed hash table used to show a bad collision pattern.

    Keys that are multiples of the table size all land in one bucket.

    """



    def _draw_hash(self):

        pass



    def _hash(self, key):

        return self._to_int(key) % self._m





# ----------------------------------------------------------------------

# Correctness

# ----------------------------------------------------------------------



def run_tests():

    failures = []



    def check(cond, msg):

        if not cond:

            failures.append(msg)



    t = HashTable(seed=1)

    check(len(t) == 0, "new table should be empty")

    check(t.search("missing") is None, "search on empty table")

    check("missing" not in t, "__contains__ on empty table")



    # Insert and update.

    t.insert("apple", 1)

    t.insert("banana", 2)

    check(t.search("apple") == 1, "basic search")

    t.insert("apple", 99)

    check(t.search("apple") == 99, "insert should update, not duplicate")

    check(len(t) == 2, "update must not change the count")



    # Delete.

    check(t.delete("apple") == 99, "delete returns the value")

    check(t.search("apple") is None, "deleted key must be gone")

    check(len(t) == 1, "count after delete")

    try:

        t.delete("apple")

        failures.append("deleting a missing key should raise KeyError")

    except KeyError:

        pass



    # Try several key types and false-like values.

    t2 = HashTable(seed=2)

    for k, v in [(0, "zero"), ("", "empty"), (False, "false"), (None, "none"),

                 (-7, "neg"), (3.5, "float"), ((1, 2), "tuple")]:

        t2.insert(k, v)

    check(t2.search(0) in ("zero", "false"), "falsy integer key")

    check(t2.search("") == "empty", "empty-string key")

    check(t2.search(None) == "none", "None as a key")

    check(t2.search(-7) == "neg", "negative key")

    check(t2.search((1, 2)) == "tuple", "tuple key")



    # Compare with dict during many random operations.

    rng = random.Random(7)

    t3, ref = HashTable(seed=3), {}

    for _ in range(20000):

        k = rng.randint(0, 2000)

        op = rng.random()

        if op < 0.55:

            v = rng.random()

            t3.insert(k, v); ref[k] = v

        elif op < 0.80:

            if t3.search(k) != ref.get(k):

                failures.append(f"search disagreed with dict on key {k}")

                break

        else:

            if k in ref:

                t3.delete(k); del ref[k]

            else:

                try:

                    t3.delete(k)

                    failures.append("delete of absent key did not raise")

                    break

                except KeyError:

                    pass

        if len(t3) != len(ref):

            failures.append("length diverged from dict")

            break

    check(dict(t3.items()) == ref, "final contents must equal the reference dict")



    # Growing and shrinking must keep every entry.

    t4 = HashTable(initial_capacity=2, seed=4)

    for i in range(5000):

        t4.insert(i, i * i)

    check(t4.load_factor <= t4.max_load, "load factor must stay under the cap")

    check(all(t4.search(i) == i * i for i in range(5000)), "grow must preserve entries")

    grown = t4.capacity

    for i in range(4900):

        t4.delete(i)

    check(t4.capacity < grown, "table should shrink after many deletions")

    check(all(t4.search(i) == i * i for i in range(4900, 5000)), "shrink must preserve entries")



    print(f"Correctness: {'all checks passed' if not failures else 'FAILURES'}")

    for f in failures:

        print("  FAIL:", f)

    print()

    return not failures





# ----------------------------------------------------------------------

# Experiments

# ----------------------------------------------------------------------



def experiment_load_factor():

    """Count key comparisons at several load factors without resizing.

    Under simple uniform hashing, an unsuccessful search examines about
    alpha entries. A successful search examines about
    1 + alpha/2 - alpha/(2n). Random keys avoid a special input pattern.

    """

    print("ELEMENTS EXAMINED vs LOAD FACTOR (random keys, resizing disabled)")

    print(f"{'alpha':>6} {'succ.':>8} {'predicted':>10} "

          f"{'unsucc.':>9} {'predicted':>10} {'max chain':>10} {'expected':>9}")

    print("-" * 68)



    m = 1024

    rng = random.Random(21)

    for alpha in (0.25, 0.5, 0.75, 1.0, 2.0, 4.0, 8.0):

        n = int(alpha * m)

        t = HashTable(initial_capacity=m, auto_resize=False, seed=11)

        keys = rng.sample(range(10**9), n)

        for k in keys:

            t.insert(k, k)



        sample = rng.sample(keys, min(3000, n))

        t.probes = 0

        for k in sample:

            t.search(k)

        succ = t.probes / len(sample)



        misses = rng.sample(range(10**9, 2 * 10**9), 3000)

        t.probes = 0

        for k in misses:

            t.search(k)

        unsucc = t.probes / len(misses)



        pred_succ = 1 + alpha / 2 - alpha / (2 * n)

        print(f"{alpha:>6.2f} {succ:>8.2f} {pred_succ:>10.2f} "

              f"{unsucc:>9.2f} {alpha:>10.2f} "

              f"{max(t.chain_lengths()):>10} {alpha:>9.2f}")

    print()





def experiment_key_structure():

    """Compare random and consecutive keys at the same load factor.

    Consecutive keys can form a pattern under this hash function. A single
    random choice of hash parameters can spread them more or less evenly.

    """

    print("CHAIN LENGTH DISTRIBUTION: random vs consecutive keys (alpha = 4)")

    print(f"{'key pattern':>14} {'max chain':>11} {'empty slots':>13} "

          f"{'Poisson pred. empty':>21} {'variance':>10} {'succ. probes':>14}")

    print("-" * 88)



    m, alpha = 1024, 4

    n = alpha * m

    rng = random.Random(22)

    import math

    poisson_empty = m * math.exp(-alpha)



    for label, keys in (("random", rng.sample(range(10**9), n)),

                        ("consecutive", list(range(n)))):

        t = HashTable(initial_capacity=m, auto_resize=False, seed=11)

        for k in keys:

            t.insert(k, k)

        st = t.stats()

        lengths = t.chain_lengths()

        var = sum((L - alpha) ** 2 for L in lengths) / m

        sample = rng.sample(keys, 2000)

        t.probes = 0

        for k in sample:

            t.search(k)

        print(f"{label:>14} {st['max_chain']:>11} {st['empty_slots']:>13} "

              f"{poisson_empty:>21.1f} {var:>10.2f} {t.probes/len(sample):>14.2f}")

    print("  Poisson variance at alpha = 4 is 4.00; mean chain length is 4.00 in both cases.")

    print()





def experiment_timing():

    """Measure time per operation as the load factor grows."""

    print("TIME PER OPERATION vs LOAD FACTOR (microseconds, resizing disabled)")

    print(f"{'alpha':>6} {'insert':>10} {'search':>10} {'delete':>10}")

    print("-" * 40)



    m = 4096

    for alpha in (0.25, 0.5, 1.0, 2.0, 4.0, 8.0):

        n = int(alpha * m)

        keys = list(range(n))



        t = HashTable(initial_capacity=m, auto_resize=False, seed=13)

        start = time.perf_counter()

        for k in keys:

            t.insert(k, k)

        ins = (time.perf_counter() - start) / n * 1e6



        rng = random.Random(14)

        sample = rng.sample(keys, min(5000, n))

        start = time.perf_counter()

        for k in sample:

            t.search(k)

        sea = (time.perf_counter() - start) / len(sample) * 1e6



        start = time.perf_counter()

        for k in sample:

            t.delete(k)

        dele = (time.perf_counter() - start) / len(sample) * 1e6



        print(f"{alpha:>6.2f} {ins:>10.3f} {sea:>10.3f} {dele:>10.3f}")

    print()





def experiment_resizing():

    """Measure the total cost of inserting n keys while the table grows."""

    print("AMORTIZED INSERTION COST WITH DYNAMIC RESIZING")

    print(f"{'n':>8} {'total ms':>10} {'us / insert':>12} {'resizes':>8} "

          f"{'rehash moves':>13} {'moves / n':>10} {'final alpha':>12}")

    print("-" * 82)



    for n in (10_000, 50_000, 100_000, 200_000):

        t = HashTable(initial_capacity=8, seed=15)

        start = time.perf_counter()

        for i in range(n):

            t.insert(i, i)

        total = (time.perf_counter() - start) * 1000

        st = t.stats()

        print(f"{n:>8,} {total:>10.1f} {total*1000/n:>12.3f} {st['resizes']:>8} "

              f"{t.rehash_moves:>13,} {t.rehash_moves/n:>10.2f} "

              f"{st['load_factor']:>12.3f}")

    print()





def experiment_adversarial():

    """Compare random hashing with a fixed hash on chosen keys.

    The keys are multiples of 1024, so the fixed hash puts every key in
    the same bucket.

    """

    print("ADVERSARIAL KEYS: fixed hash vs universal hash")

    print(f"{'n':>7} {'table':>12} {'max chain':>11} {'collisions':>11} "

          f"{'search us':>11}")

    print("-" * 56)



    m = 1024

    for n in (1000, 2000, 4000):

        keys = [i * m for i in range(1, n + 1)]   # all map to bucket 0 with k mod m



        for label, cls in (("fixed", BadHashTable), ("universal", HashTable)):

            t = cls(initial_capacity=m, auto_resize=False, seed=16)

            for k in keys:

                t.insert(k, k)



            probe_keys = keys[::max(1, n // 200)]

            start = time.perf_counter()

            for k in probe_keys:

                t.search(k)

            us = (time.perf_counter() - start) / len(probe_keys) * 1e6



            print(f"{n:>7,} {label:>12} {max(t.chain_lengths()):>11,} "

                  f"{t.collisions:>11,} {us:>11.2f}")

        print()





if __name__ == "__main__":

    print()

    if not run_tests():

        sys.exit(1)

    experiment_load_factor()

    experiment_key_structure()

    experiment_timing()

    experiment_resizing()

    experiment_adversarial()
