export default function SimpleListPage({ title, text }: { title: string; text: string }) {
  return (
    <div className="panel">
      <h2>{title}</h2>
      <p>{text}</p>
    </div>
  );
}
