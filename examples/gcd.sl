fn gcd(a, b) {
    while (b != 0) {
        let t = b;
        b = a % b;
        a = t;
    }
    return a;
}
print gcd(1071, 462);   // 21
print gcd(96, 36);      // 12
