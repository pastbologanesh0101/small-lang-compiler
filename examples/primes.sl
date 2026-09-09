fn is_prime(n) {
    if (n < 2) { return false; }
    let d = 2;
    while (d * d <= n) {
        if (n % d == 0) { return false; }
        d = d + 1;
    }
    return true;
}
let n = 2;
let count = 0;
while (count < 10) {
    if (is_prime(n)) { print n; count = count + 1; }
    n = n + 1;
}
