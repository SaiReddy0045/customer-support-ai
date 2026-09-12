import {
  FiWatch,
  FiHeadphones,
  FiBatteryCharging,
  FiWifi,
  FiCamera,
  FiSun,
  FiSmartphone,
} from "react-icons/fi";
import { BsKeyboard, BsEarbuds } from "react-icons/bs";
import { MdOutlineWatch, MdSpeaker } from "react-icons/md";

const ICONS = {
  watch: FiWatch,
  earbuds: BsEarbuds,
  speaker: MdSpeaker,
  powerbank: FiBatteryCharging,
  headphones: FiHeadphones,
  plug: FiWifi,
  keyboard: BsKeyboard,
  camera: FiCamera,
  band: MdOutlineWatch,
  case: FiSmartphone,
  lamp: FiSun,
  neckband: FiHeadphones,
};

function ProductImage({ icon = "watch", name, large = false }) {
  const Icon = ICONS[icon] || FiWatch;
  return (
    <div className={`product-visual ${large ? "large" : ""}`} aria-hidden="true">
      <Icon />
      <span>{name}</span>
    </div>
  );
}

export default ProductImage;
