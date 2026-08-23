"use client";

import { useEffect, useRef, useState } from "react";
// Types only — erased at build, so three still enters the bundle solely via the
// dynamic import() in the effect below. Aliased so it can't collide with the
// runtime `THREE` binding inside that effect.
import type * as ThreeNS from "three";

/** Hero "router · live view": a layered target, six model nodes on a slow orbit,
 *  and arrows firing from a random node into the bullseye. three.js is loaded
 *  with a dynamic `import()` inside the effect so it never enters the initial
 *  bundle and never runs on the server.
 *
 *  Under reduced motion the scene is still built and rendered — one frame, then
 *  no loop: a still 3D target with no orbit, no arrows, no parallax. Skipping it
 *  outright would leave those users staring at an empty box, and "reduce motion"
 *  asks for less movement, not less content. The CSS ring below is the fallback
 *  for the case that really has nothing to show: WebGL unavailable. */
export function HeroScene() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  // Drives the CSS target underneath: it shows until (and unless) the canvas has
  // painted, since the canvas is transparent and the two would otherwise overlap.
  const [live, setLive] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let cleanup: (() => void) | undefined;
    let cancelled = false;

    (async () => {
      const THREE = await import("three");
      if (cancelled) return;

      const w = canvas.clientWidth || 460;
      const h = canvas.clientHeight || 460;
      const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      renderer.setSize(w, h, false);

      const scene = new THREE.Scene();
      const cam = new THREE.PerspectiveCamera(38, w / h, 0.1, 100);
      cam.position.set(0, 0.3, 13.6);
      scene.add(new THREE.AmbientLight(0xb5abfc, 0.5));
      const key = new THREE.DirectionalLight(0xffffff, 1.15);
      key.position.set(4, 6, 8);
      scene.add(key);
      const rim = new THREE.DirectionalLight(0x968ae0, 0.9);
      rim.position.set(-6, -3, 2);
      scene.add(rim);

      const root = new THREE.Group();
      root.rotation.x = -0.12;
      scene.add(root);
      const target = new THREE.Group();
      root.add(target);

      const discs: [number, number][] = [
        [2.9, 0x2b2741],
        [2.25, 0x423a6a],
        [1.62, 0x5d5294],
        [1.0, 0x796cbf],
      ];
      discs.forEach(([r, col], i) => {
        const disc = new THREE.Mesh(
          new THREE.CylinderGeometry(r, r, 0.2, 72),
          new THREE.MeshStandardMaterial({ color: col, roughness: 0.62, metalness: 0.12 }),
        );
        disc.rotation.x = Math.PI / 2;
        disc.position.z = i * 0.17;
        target.add(disc);
        const ring = new THREE.Mesh(
          new THREE.TorusGeometry(r, 0.028, 8, 96),
          new THREE.MeshStandardMaterial({
            color: 0xd2cefd,
            emissive: 0x9184d9,
            emissiveIntensity: 0.5,
            roughness: 0.3,
          }),
        );
        ring.position.z = i * 0.17 + 0.11;
        target.add(ring);
      });

      const bull = new THREE.Mesh(
        new THREE.SphereGeometry(0.44, 40, 40),
        new THREE.MeshStandardMaterial({
          color: 0xe7e5fe,
          emissive: 0x968ae0,
          emissiveIntensity: 0.85,
          roughness: 0.25,
        }),
      );
      bull.position.z = 0.78;
      target.add(bull);

      // Model name plates are canvas textures — cheaper than any text geometry
      // and they stay crisp because the sprite never scales past its 512px map.
      const label = (text: string) => {
        const c = document.createElement("canvas");
        c.width = 512;
        c.height = 96;
        const g = c.getContext("2d")!;
        g.fillStyle = "rgba(22,24,38,0.86)";
        g.strokeStyle = "#5d5294";
        g.lineWidth = 3;
        const r = 26;
        g.beginPath();
        g.moveTo(r, 6);
        g.lineTo(506 - r, 6);
        g.quadraticCurveTo(506, 6, 506, 6 + r);
        g.lineTo(506, 90 - r);
        g.quadraticCurveTo(506, 90, 506 - r, 90);
        g.lineTo(r, 90);
        g.quadraticCurveTo(6, 90, 6, 90 - r);
        g.lineTo(6, 6 + r);
        g.quadraticCurveTo(6, 6, r, 6);
        g.closePath();
        g.fill();
        g.stroke();
        g.fillStyle = "#d2cefd";
        g.font = "500 40px 'JetBrains Mono', ui-monospace, monospace";
        g.textBaseline = "middle";
        g.textAlign = "center";
        g.fillText(text, 256, 50);
        const sp = new THREE.Sprite(
          new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), transparent: true }),
        );
        sp.scale.set(2.1, 0.39, 1);
        return sp;
      };

      const NAMES = [
        "gpt-oss-120b",
        "qwen3.6-27b",
        "nemotron-3-ultra",
        "minimax-m3",
        "gemma4-31b",
        "gpt-oss-20b",
      ];
      const orbit = new THREE.Group();
      orbit.rotation.x = 0.22;
      root.add(orbit);
      const nodes = NAMES.map((n, i) => {
        const a = (i / NAMES.length) * Math.PI * 2;
        const pos = new THREE.Vector3(
          Math.cos(a) * 3.75,
          Math.sin(a) * 3.95,
          Math.sin(a * 2) * 0.5,
        );
        const chip = new THREE.Mesh(
          new THREE.BoxGeometry(0.5, 0.5, 0.14),
          new THREE.MeshStandardMaterial({
            color: 0x3f424d,
            emissive: 0x423a6a,
            emissiveIntensity: 0.35,
            roughness: 0.45,
            metalness: 0.3,
          }),
        );
        chip.position.copy(pos);
        orbit.add(chip);
        const sp = label(n);
        sp.position.set(pos.x, pos.y - 0.62, pos.z);
        orbit.add(sp);
        const line = new THREE.Line(
          new THREE.BufferGeometry().setFromPoints([pos.clone(), new THREE.Vector3(0, 0, 0)]),
          new THREE.LineBasicMaterial({ color: 0x5d5294, transparent: true, opacity: 0.28 }),
        );
        orbit.add(line);
        return { chip, line, pos, sp };
      });

      const arrow = () => {
        const g = new THREE.Group();
        const shaft = new THREE.Mesh(
          new THREE.CylinderGeometry(0.045, 0.045, 1.9, 12),
          new THREE.MeshStandardMaterial({ color: 0x292b31, roughness: 0.6 }),
        );
        shaft.rotation.x = Math.PI / 2;
        g.add(shaft);
        const tip = new THREE.Mesh(
          new THREE.ConeGeometry(0.11, 0.34, 16),
          new THREE.MeshStandardMaterial({
            color: 0xe7e5fe,
            emissive: 0x9184d9,
            emissiveIntensity: 0.4,
            roughness: 0.3,
          }),
        );
        tip.rotation.x = Math.PI / 2;
        tip.position.z = 1.1;
        g.add(tip);
        [0.28, -0.28].forEach((o) => {
          const f = new THREE.Mesh(
            new THREE.BoxGeometry(0.02, 0.3, 0.34),
            new THREE.MeshStandardMaterial({ color: 0x9184d9, roughness: 0.5 }),
          );
          f.position.set(o * 0.4, o * 0.25, -0.85);
          f.rotation.z = o;
          g.add(f);
        });
        return g;
      };

      const flying: {
        a: ThreeNS.Group;
        from: ThreeNS.Vector3;
        to: ThreeNS.Vector3;
        t: number;
      }[] = [];
      const landed: ThreeNS.Group[] = [];
      let clock = 0;
      let nextShot = 0.7;
      let mx = 0;
      let my = 0;
      let tmx = 0;
      let tmy = 0;

      const shoot = () => {
        const n = nodes[Math.floor(Math.random() * nodes.length)];
        const a = arrow();
        const from = n.pos.clone().multiplyScalar(1.35);
        from.z -= 4.5;
        a.position.copy(from);
        const to = new THREE.Vector3(0, 0, 1.1).add(
          new THREE.Vector3((Math.random() - 0.5) * 0.34, (Math.random() - 0.5) * 0.34, 0),
        );
        root.add(a);
        flying.push({ a, from, to, t: 0 });
        // The flash is the whole point: it reads as "this node was routed to".
        n.line.material.opacity = 0.95;
        n.chip.material.emissiveIntensity = 1.4;
      };

      const onMove = (e: PointerEvent) => {
        const b = canvas.getBoundingClientRect();
        tmx = ((e.clientX - b.left) / b.width - 0.5) * 2;
        tmy = ((e.clientY - b.top) / b.height - 0.5) * 2;
      };
      const onLeave = () => {
        tmx = 0;
        tmy = 0;
      };
      if (!still) {
        canvas.addEventListener("pointermove", onMove);
        canvas.addEventListener("pointerleave", onLeave);
      }

      const onResize = () => {
        const nw = canvas.clientWidth;
        const nh = canvas.clientHeight;
        if (!nw || !nh) return;
        cam.aspect = nw / nh;
        cam.updateProjectionMatrix();
        renderer.setSize(nw, nh, false);
      };
      window.addEventListener("resize", onResize);

      let raf = 0;
      let last = performance.now();
      const tick = () => {
        const now = performance.now();
        const dt = Math.min((now - last) / 1000, 0.05);
        last = now;
        clock += dt;

        mx += (tmx - mx) * 0.06;
        my += (tmy - my) * 0.06;
        root.rotation.y = 0.32 * mx + Math.sin(clock * 0.22) * 0.06;
        root.rotation.x = -0.12 - 0.22 * my;
        orbit.rotation.z += dt * 0.14;
        bull.material.emissiveIntensity = 0.7 + Math.sin(clock * 2.1) * 0.28;
        bull.scale.setScalar(1 + Math.sin(clock * 2.1) * 0.05);

        nodes.forEach((n) => {
          n.line.material.opacity += (0.28 - n.line.material.opacity) * dt * 2.2;
          n.chip.material.emissiveIntensity +=
            (0.35 - n.chip.material.emissiveIntensity) * dt * 2.2;
          n.sp.material.rotation = -orbit.rotation.z;
        });

        if (clock > nextShot) {
          shoot();
          nextShot = clock + 1.5 + Math.random() * 1.2;
        }

        for (let i = flying.length - 1; i >= 0; i--) {
          const f = flying[i];
          f.t = Math.min(1, f.t + dt / 0.75);
          f.a.position.lerpVectors(f.from, f.to, 1 - Math.pow(1 - f.t, 3));
          f.a.lookAt(0, 0, 2.4);
          if (f.t >= 1) {
            flying.splice(i, 1);
            landed.push(f.a);
            if (landed.length > 5) root.remove(landed.shift()!);
          }
        }
        renderer.render(scene, cam);
        raf = requestAnimationFrame(tick);
      };

      if (still) {
        // One composed frame, never a loop. The orbit stays at 0 so the six
        // nodes straddle the bottom of the ring instead of one sitting at the
        // very bottom, where its label would be clipped by the stage edge —
        // transient while spinning, permanent when frozen.
        renderer.render(scene, cam);
      } else {
        tick();
      }
      setLive(true);

      cleanup = () => {
        cancelAnimationFrame(raf);
        setLive(false);
        canvas.removeEventListener("pointermove", onMove);
        canvas.removeEventListener("pointerleave", onLeave);
        window.removeEventListener("resize", onResize);
        renderer.dispose();
      };
    })();

    return () => {
      cancelled = true;
      cleanup?.();
    };
  }, []);

  return (
    <div className="lp-stage">
      {!live && <div className="lp-stage-static" aria-hidden />}
      <canvas ref={canvasRef} className="lp-canvas" />
      <span className="lp-stage-label lp-mono">router · live view</span>
    </div>
  );
}
