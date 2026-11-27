/**
 * Hardware ordering configuration.
 *
 * Ordering is a REQUEST flow (no online payment): the buyer sends their details and the
 * iShara team replies with price and delivery. How requests are delivered is set with
 * environment variables (see website/README.md):
 *   ORDER_EMAIL_TO + RESEND_API_KEY  -> server sends the request by email (Resend)
 *   NEXT_PUBLIC_ORDER_EMAIL          -> the form opens the visitor's email app instead
 *   neither                          -> the page shows "Ordering opens soon"
 * Prices are not published until set here.
 */
export type Kit = {
  id: string;
  name: string;
  summary: string;
  includes: string[];
  price: string | null; // e.g. "PKR 6,500"; null = "Price on request"
  available: boolean;
};

export const kits: Kit[] = [
  {
    id: "assembled",
    name: "Assembled headband",
    summary: "Ready to wear. Flashed with the latest firmware and tested.",
    includes: ["ESP32 + MPU6050 headband, assembled", "3.7 V 1200 mAh Li-Po battery", "USB-C charging", "Firmware installed"],
    price: null,
    available: true,
  },
  {
    id: "diy",
    name: "DIY parts kit",
    summary: "All parts to build your own, with the open wiring guide.",
    includes: ["ESP32 dev board", "MPU6050 module", "Li-Po battery + USB-C charger", "Buzzer, wires, headband + foam"],
    price: null,
    available: true,
  },
];

export const billOfMaterials = [
  ["ESP32 dev board (USB-C)", "Bluetooth LE: HID mouse + iShara data service"],
  ["MPU6050 module (GY-521)", "Accelerometer + gyroscope, I²C"],
  ["Li-Po 3.7 V 1200 mAh", "Power"],
  ["USB-C Li-Po charger (HW-373)", "Charging"],
  ["Active buzzer", "One beep when Bluetooth connects"],
  ["Headband + foam support", "Holds the electronics on the forehead"],
] as const;

export const wiring = [
  ["VCC", "3V3"],
  ["GND", "GND"],
  ["SDA", "D21"],
  ["SCL", "D22"],
  ["AD0", "GND"],
] as const;
