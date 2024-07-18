import React, { useEffect } from "react";
import "../../../../common.css";
import "./toggle-rays.css";
import { useRaysContext } from "../../../../Contexts/RaysContext";
import ToggleScatterPoints from "../toggle-scatter-points/ToggleScatterPoints";
import RaysPlayback from "../rays-playback/RaysPlayback";
import ShowAllRays from "../show-all-rays/ShowAllRays";
import { fetchJSON } from "../../../../utils/fetch";
import { initializeRays } from "../../../../data-utils/initRays";

const ToggleRays = () => {
  const {
    rays,
    setRays,
    showAllRays,
    toggleShowAllRays,
    showRays,
    toggleRays,
  } = useRaysContext();

  const handleClick = () => {
    if (rays.rays.length === 0) {
      console.log("initialize rays");
      fetchJSON("../particles.json").then((data) => {
        if (data) {
          const rayData = initializeRays(data);
          setRays(rayData);
        } else {
          console.warn("Particle data is missing");
        }
      });
    }
    toggleRays();
  };

  return (
    <div id="toggle-rays" className="row">
      <button onClick={handleClick}>
        {showRays ? "Hide Rays" : "Show Rays"}
      </button>
      {showRays && showAllRays ? <ShowAllRays text="Show PlayBack" /> : null}
      {showRays && !showAllRays ? <ShowAllRays text="Show All" /> : null}
      {showRays && !showAllRays ? <RaysPlayback /> : null}
      {showRays ? <ToggleScatterPoints /> : null}
    </div>
  );
};

export default ToggleRays;