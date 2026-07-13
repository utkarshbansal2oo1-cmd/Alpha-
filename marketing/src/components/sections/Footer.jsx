import Logo from "../nav/Logo";

const COLUMNS = [
  { title: "Product", links: ["Live Demo", "Architecture", "Enterprise"] },
  { title: "Company", links: ["About", "Vision"] },
  { title: "Legal", links: ["Privacy", "Terms"] },
];

export default function Footer() {
  return (
    <footer className="relative border-t border-white/5 py-20 px-5">
      <div className="max-w-[1280px] mx-auto flex flex-col md:flex-row justify-between gap-12">
        <div>
          <Logo />
        </div>
        <div className="flex gap-16">
          {COLUMNS.map((col) => (
            <div key={col.title}>
              <h4 className="text-caption uppercase tracking-[0.08em] text-text-tertiary mb-4">{col.title}</h4>
              <ul className="space-y-2">
                {col.links.map((link) => (
                  <li key={link}>
                    <a href="#top" className="text-sm text-text-secondary hover:text-text-primary transition-colors">
                      {link}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
      <div className="max-w-[1280px] mx-auto mt-16 pt-8 border-t border-white/5">
        <p className="text-sm text-text-tertiary">Stop searching. Start hiring intelligently.</p>
      </div>
    </footer>
  );
}
