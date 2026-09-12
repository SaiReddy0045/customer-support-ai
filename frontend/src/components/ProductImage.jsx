const IMAGE_BY_ICON = {
  watch: "/images/watch.jpg",
  earbuds: "/images/earbuds.jpg",
  speaker: "/images/speaker.jpg",
  powerbank: "/images/powerbank.jpg",
  headphones: "/images/headphones.jpg",
  plug: "/images/plug.jpg",
  keyboard: "/images/keyboard.jpg",
  camera: "/images/camera.jpg",
  band: "/images/band.jpg",
  case: "/images/case.jpg",
  lamp: "/images/lamp.jpg",
  neckband: "/images/neckband.jpg",
};

function ProductImage({ product, src, icon, name, alt, large = false }) {
  const imageSrc =
    src ||
    product?.image ||
    IMAGE_BY_ICON[icon || product?.icon] ||
    "/images/headphones.jpg";
  const label = alt || product?.name || name || "Product photo";

  return (
    <div className={`product-photo ${large ? "large" : ""}`}>
      <img src={imageSrc} alt={label} />
    </div>
  );
}

export default ProductImage;
