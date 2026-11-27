/**
 * The real iShara prototype, front view: a fabric/foam headband with the electronics
 * mounted openly on the forehead section: ESP32 dev board (bottom), separate MPU6050
 * module (top right), Li-Po battery (left), USB-C charger board, buzzer and wires.
 * Drawn from photos of the actual hardware; not a concept product.
 */
export function DeviceIllustration() {
  return (
    <svg viewBox="0 0 760 360" role="img" aria-labelledby="dev-t dev-d">
      <title id="dev-t">iShara headband prototype</title>
      <desc id="dev-d">
        A grey fabric headband with an ESP32 board, an MPU6050 sensor module, a Li-Po battery, a USB-C charger board and a buzzer mounted on the forehead section, connected by wires.
      </desc>
      <defs>
        <pattern id="fabric" width="6" height="6" patternUnits="userSpaceOnUse">
          <rect width="6" height="6" fill="#b9b9be" />
          <circle cx="2" cy="2" r="1.1" fill="#c9c9ce" />
          <circle cx="5" cy="5" r="0.9" fill="#a9a9ae" />
        </pattern>
      </defs>

      {/* fabric / foam headband */}
      <path d="M20 200 C 140 150, 620 150, 740 200 L 740 262 C 620 214, 140 214, 20 262 Z" fill="url(#fabric)" />
      <rect x="196" y="72" width="368" height="236" rx="26" fill="#ececef" stroke="#d6d6db" />

      {/* Li-Po battery */}
      <g>
        <rect x="214" y="96" width="120" height="190" rx="8" fill="#d9d9de" stroke="#b8b8be" />
        <rect x="214" y="256" width="120" height="30" rx="4" fill="#e3c24a" />
        <text x="274" y="180" textAnchor="middle" fontSize="13" fill="#6e6e73" transform="rotate(-90 274 180)">3.7V 1200mAh Li-Po</text>
      </g>

      {/* USB-C charger board */}
      <rect x="350" y="96" width="70" height="92" rx="6" fill="#2a5db0" />
      <rect x="370" y="100" width="30" height="16" rx="5" fill="#c7c7cc" />
      <text x="385" y="160" textAnchor="middle" fontSize="11" fill="#dbe7ff">charger</text>

      {/* MPU6050 module (separate, top right) */}
      <g>
        <rect x="436" y="90" width="112" height="84" rx="6" fill="#1f4fa3" />
        <circle cx="448" cy="102" r="6" fill="#ececef" />
        <circle cx="536" cy="102" r="6" fill="#ececef" />
        <rect x="478" y="116" width="26" height="26" rx="3" fill="#1d1d1f" />
        {Array.from({ length: 8 }).map((_, i) => (
          <circle key={i} cx={446 + i * 13} cy={164} r="3.2" fill="#c7c7cc" />
        ))}
        <text x="492" y="196" textAnchor="middle" fontSize="12" fill="#6e6e73">MPU6050</text>
      </g>

      {/* ESP32 dev board (bottom) */}
      <g>
        <rect x="350" y="206" width="198" height="88" rx="6" fill="#1d1d1f" />
        <rect x="470" y="218" width="64" height="62" rx="4" fill="#3a3a3c" />
        <rect x="360" y="236" width="26" height="22" rx="5" fill="#c7c7cc" />
        <circle cx="530" cy="290" r="3" fill="#ff3b30" />
        {Array.from({ length: 14 }).map((_, i) => (
          <circle key={i} cx={362 + i * 13} cy={212} r="2.4" fill="#a1a1a6" />
        ))}
        <text x="430" y="276" textAnchor="middle" fontSize="12" fill="#a1a1a6">ESP32</text>
      </g>

      {/* buzzer */}
      <circle cx="566" cy="262" r="16" fill="#1d1d1f" />
      <circle cx="566" cy="262" r="4" fill="#3a3a3c" />

      {/* wires */}
      <g fill="none" strokeWidth="3" strokeLinecap="round">
        <path d="M456 170 C 430 196, 420 200, 400 210" stroke="#2f6fe8" />
        <path d="M470 170 C 452 200, 440 204, 420 210" stroke="#34c759" />
        <path d="M486 170 C 472 196, 470 204, 460 210" stroke="#ff9500" />
        <path d="M500 170 C 500 196, 496 204, 490 210" stroke="#af52de" />
        <path d="M334 200 C 344 200, 350 192, 360 188" stroke="#ff3b30" />
        <path d="M334 214 C 346 214, 352 206, 362 200" stroke="#1d1d1f" />
        <path d="M548 250 C 556 250, 556 254, 552 258" stroke="#1d1d1f" />
      </g>

      {/* labels */}
      <g fontSize="13" fill="#6e6e73" fontWeight="500">
        <text x="20" y="300">fabric / foam headband</text>
        <text x="600" y="120">sensor faces forward</text>
        <text x="600" y="276">buzzer</text>
      </g>
    </svg>
  );
}
