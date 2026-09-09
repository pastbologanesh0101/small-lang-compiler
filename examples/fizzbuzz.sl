fn divisible(n, d) { return n % d == 0; }

let i = 1;
while (i <= 20) {
    if (divisible(i, 15))      { print 3535; }   // "FizzBuzz" sentinel
    else if (divisible(i, 3))  { print 33; }     // "Fizz"
    else if (divisible(i, 5))  { print 55; }     // "Buzz"
    else                       { print i; }
    i = i + 1;
}
