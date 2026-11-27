import Link from "next/link";

export default function NotFound() {
  return (
    <section className="wrap hero">
      <h2>Page not found</h2>
      <p className="lead">This page doesn&apos;t exist.</p>
      <div className="row"><Link href="/" className="btn btn-primary">Back to home</Link></div>
    </section>
  );
}
