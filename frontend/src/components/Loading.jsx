function Loading({ label = "Loading..." }) {
  return (
    <div className="loading-block" role="status">
      <div className="loading">
        <span />
        <span />
        <span />
      </div>
      <p>{label}</p>
    </div>
  );
}

export default Loading;
