// Three.js CAD viewer. Loaded lazily: the Three modules are only fetched
// when a page actually mounts a viewer. Supports .glb/.gltf and .stl.

// Options:
//   interactive — false mounts the board as decoration: it spins on its own
//   and ignores the pointer entirely, so clicks and scrolls pass through to
//   the page behind it. Defaults to true (grab, orbit, click-to-zoom).
//   flip — open on the board's other face. Which face the camera finds first
//   depends on how the board was exported, so a board whose front comes up
//   facing away sets this (projects.json: "modelFlip": true).
export async function mountViewer(selector, modelUrl, { interactive = true, flip = false } = {}) {
  const host = document.querySelector(selector);
  if (!host) return;

  const status = host.querySelector(".viewer-status");
  const say = msg => { if (status) { status.hidden = false; status.textContent = msg; } };
  const hideStatus = () => { if (status) status.hidden = true; };

  say("Loading 3D model…");

  // Bail out with a friendly message rather than a stack trace when the
  // model file hasn't been exported yet.
  const head = await fetch(modelUrl, { method: "HEAD" }).catch(() => null);
  if (!head || !head.ok) {
    say(`No model yet — export ${modelUrl.split("/").pop()} into assets/models/ to light this up.`);
    return;
  }

  const THREE = await import("three");
  const { OrbitControls } = await import("three/addons/controls/OrbitControls.js");

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, 16 / 10, 0.1, 2000);
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  host.prepend(renderer.domElement);

  // Calibrated rig: linear tone mapping (ACES pulls the saturation out of the
  // greens), a sliver of environment so the metal parts have something to
  // reflect, and only enough light to model the board's relief.
  const { RoomEnvironment } = await import("three/addons/environments/RoomEnvironment.js");
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environmentIntensity = 0.08;
  renderer.toneMapping = THREE.LinearToneMapping;
  renderer.toneMappingExposure = 1.0;

  scene.add(new THREE.HemisphereLight(0xffffff, 0xcccccc, 0.08));
  for (const [x, y, z, intensity] of [
    [ 3,  5,  4, 0.25],
    [-3, -5, -4, 0.2],
    [-4,  2,  5, 0.15],
    [ 4, -2, -5, 0.15],
  ]) {
    const light = new THREE.DirectionalLight(0xffffff, intensity);
    light.position.set(x, y, z);
    scene.add(light);
  }

  const headlight = new THREE.DirectionalLight(0xffffff, 0.4);
  scene.add(headlight);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;

  // A reduced-motion preference switches the idle spin off for good.
  const spins = !matchMedia("(prefers-reduced-motion: reduce)").matches;
  controls.autoRotate = spins;
  controls.autoRotateSpeed = 2.4;

  let touched = false;

  if (!interactive) {
    // Decoration: the spin never yields and the canvas is invisible to the
    // pointer, so the board can sit behind page copy without swallowing
    // clicks, drags or scrolls.
    controls.enabled = false;
    renderer.domElement.style.pointerEvents = "none";
  } else {
    // Idle spin: the board turns on its own so it reads as something you can
    // grab. It yields the moment someone takes hold and picks up again from
    // wherever they left it once they've been still for a beat.
    let idleTimer, dragging = false;
    const holdSpin = () => { clearTimeout(idleTimer); controls.autoRotate = false; };
    const resumeSpin = () => {
      clearTimeout(idleTimer);
      if (spins && !dragging) idleTimer = setTimeout(() => { controls.autoRotate = true; }, 2500);
    };
    controls.addEventListener("start", () => { dragging = true; holdSpin(); });
    controls.addEventListener("end", () => { dragging = false; resumeSpin(); });

    // Don't trap the page scroll: the wheel only zooms once the viewer has been
    // clicked, and clicking away hands scrolling back to the document.
    controls.enableZoom = false;
    const takeOver = () => { touched = true; holdSpin(); resumeSpin(); };
    const setActive = on => {
      if (on) takeOver();
      controls.enableZoom = on;
      host.classList.toggle("is-active", on);
    };
    host.addEventListener("click", () => setActive(true));
    host.addEventListener("pointerdown", takeOver);
    document.addEventListener("click", e => {
      if (!host.contains(e.target)) setActive(false);
    });
  }

  let object;
  if (/\.stl$/i.test(modelUrl)) {
    const { STLLoader } = await import("three/addons/loaders/STLLoader.js");
    const geometry = await new STLLoader().loadAsync(modelUrl);
    geometry.computeVertexNormals();
    object = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({
      color: 0xb0b6bd, metalness: 0.25, roughness: 0.5,
    }));
  } else {
    const { GLTFLoader } = await import("three/addons/loaders/GLTFLoader.js");
    object = (await new GLTFLoader().loadAsync(modelUrl)).scene;
  }
  scene.add(object);

  // Frame the model: centre it on the origin, then back the camera off by
  // enough to fit its bounding sphere in view.
  const box = new THREE.Box3().setFromObject(object);
  const centre = box.getCenter(new THREE.Vector3());
  object.position.sub(centre);
  const size = box.getSize(new THREE.Vector3());
  const radius = size.length() / 2 || 1;

  // A board is a slab, so its thinnest axis is the face normal. Look straight
  // down that axis and the board reads flat-on; the other two axes become the
  // screen's horizontal and vertical.
  const axes = [0, 1, 2];
  const normal = axes.reduce((a, b) => (size.getComponent(a) <= size.getComponent(b) ? a : b));
  const [across, up] = axes.filter(a => a !== normal);

  const unit = i => new THREE.Vector3(+(i === 0), +(i === 1), +(i === 2));
  camera.up.copy(unit(up));

  // Distance that fits both in-plane extents at the current aspect ratio,
  // whichever is tighter, plus a margin and half the board's own depth.
  let framed = false;
  const frame = () => {
    const halfFov = THREE.MathUtils.degToRad(camera.fov) / 2;
    const fitUp = size.getComponent(up) / 2 / Math.tan(halfFov);
    const fitAcross = size.getComponent(across) / 2 / (Math.tan(halfFov) * camera.aspect);
    const distance = Math.max(fitUp, fitAcross) * 1.15 + size.getComponent(normal) / 2;

    // Re-framing after a resize keeps whatever heading the idle spin has
    // reached, so the board doesn't snap back to its opening shot.
    const heading = framed
      ? camera.position.clone().normalize()
      : unit(normal).multiplyScalar(flip ? 1 : -1);
    camera.position.copy(heading.multiplyScalar(distance));
    framed = true;
    camera.near = radius / 100;
    camera.far = radius * 100;
    camera.updateProjectionMatrix();
    controls.target.set(0, 0, 0);
    controls.update();
  };

  const resize = () => {
    const { clientWidth: w, clientHeight: h } = host;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    // Keep re-framing until the viewer is touched, so the opening shot always
    // fits; after that the camera belongs to whoever is driving it.
    if (!touched) frame();
  };
  new ResizeObserver(resize).observe(host);
  resize();
  frame();

  hideStatus();
  renderer.setAnimationLoop(() => {
    controls.update();
    headlight.position.copy(camera.position);
    renderer.render(scene, camera);
  });

  // Handles for tools that need to reach into the loaded board:
  // tools/mask-color.html repaints materials live so a colour can be judged
  // under this exact light rig, and tools/board-shot.html stops the spin,
  // re-frames flat-on and reads the canvas back as a still.
  return { THREE, scene, object, renderer, camera, controls, frame };
}
