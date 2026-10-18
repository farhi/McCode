// mcdisplay-export.ts
//
// 3D model export for the mcdisplay-webgl React (Vite) app.
// Exports the instrument geometry (per-component colors) and all particle
// rays (with their LUT speed colors), in one of: glb, gltf (JSON), x3d, obj+mtl.
//
// Usage in ThreeCanvas.tsx:
//   import { ExportMenu } from "../mcdisplay-export";
//   ... inside the returned JSX:
//   <ExportMenu getRoot={() => sceneRef.current} />
//
// The module is dependency-free (no three.js example exporters required):
// glTF/GLB, X3D and OBJ+MTL writers are implemented below.

import * as THREE from "three";

type ExportFormat = "glb" | "gltf" | "x3d" | "obj";

interface CollectedObject {
    name: string;
    color: [number, number, number];
    positions: Float32Array;
    indices: Int32Array | number[];
    isLine: boolean;
}

// ---------------------------------------------------------------------------
// generic helpers
// ---------------------------------------------------------------------------

function downloadBlob(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 5000);
}

function downloadText(text: string, filename: string, mime?: string) {
    downloadBlob(new Blob([text], { type: mime || "text/plain" }), filename);
}

// Collect triangles and polylines of a scene graph with world transforms baked in.
// Grid helpers, axes helpers and lights are skipped.
// Ray polylines are converted to segment pairs (v0,v1, v1,v2, ...).
export function collectGeometry(root: THREE.Object3D): CollectedObject[] {
    const objects: CollectedObject[] = [];
    root.updateMatrixWorld(true);

    root.traverse((obj: any) => {
        const isMesh = obj.isMesh;
        const isLine = obj.isLine || obj.isLineSegments;
        if (!isMesh && !isLine) return; // skip lights, plain Object3D groups, cameras
        if (obj instanceof THREE.GridHelper) return;
        if (obj instanceof THREE.AxesHelper) return;
        if (obj.name && obj.name.indexOf("grid") === 0) return;

        const geom: THREE.BufferGeometry = obj.geometry;
        if (!geom || !geom.attributes || !geom.attributes.position) return;

        const pos = geom.attributes.position as THREE.BufferAttribute;
        const count = pos.count;

        // bake world matrix into positions
        const v = new THREE.Vector3();
        const positions = new Float32Array(count * 3);
        for (let i = 0; i < count; i++) {
            v.fromBufferAttribute(pos, i).applyMatrix4(obj.matrixWorld);
            positions[i * 3] = v.x;
            positions[i * 3 + 1] = v.y;
            positions[i * 3 + 2] = v.z;
        }

        // indices
        let indices: Int32Array | number[];
        if (isLine) {
            indices = [];
            for (let i = 1; i < count; i++) indices.push(i - 1, i);
        } else if (geom.index) {
            indices = new Int32Array(geom.index.array as ArrayLike<number>);
        } else {
            indices = new Int32Array(count);
            for (let i = 0; i < count; i++) indices[i] = i;
        }

        // material color
        let color: [number, number, number] = [0.8, 0.8, 0.8];
        if (obj.material && obj.material.color) {
            color = [obj.material.color.r, obj.material.color.g, obj.material.color.b];
        }

        // a unique-ish name: nearest named ancestor (component name) or own name
        let name: string = obj.name || "";
        if (!name) {
            let p: any = obj.parent;
            while (p && !p.name) p = p.parent;
            name = p ? p.name : "object";
        }
        name = name + "_" + objects.length;

        objects.push({ name, color, positions, indices, isLine });
    });
    return objects;
}

// ---------------------------------------------------------------------------
// top-level entry
// ---------------------------------------------------------------------------

export function exportModel(
    getRoot: () => THREE.Object3D | null,
                            format: ExportFormat,
                                includeRays: boolean
) {
    const root = getRoot();
    if (!root) {
        alert("Scene not ready yet.");
        return;
    }

    const stamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);

    if (format === "glb") {
        writeGLB(root, "mcdisplay-" + stamp + ".glb");
    } else if (format === "gltf") {
        downloadText(JSON.stringify(buildGLTF(root).json, null, 2),
                     "mcdisplay-" + stamp + ".gltf", "model/gltf+json");
    } else if (format === "x3d") {
        writeX3D(root, "mcdisplay-" + stamp + ".x3d");
    } else if (format === "obj") {
        writeOBJ(root, "mcdisplay-" + stamp);
    }
}

// ---------------------------------------------------------------------------
// glTF 2.0 / GLB writer (minimal, self-contained)
// ---------------------------------------------------------------------------

function buildGLTF(root: THREE.Object3D) {
    const objects = collectGeometry(root);

    const json: any = {
        asset: { version: "2.0", generator: "mcdisplay-export" },
        scene: 0,
        scenes: [{ nodes: [0] }],
        nodes: [{ name: "mcdisplay", children: [] }],
        meshes: [],
        materials: [],
        accessors: [],
        bufferViews: [],
        buffers: [],
    };

    const buffers: ArrayBuffer[] = [];

    function addBufferView(arrayBuffer: ArrayBuffer, target?: number): number {
        let offset = 0;
        for (let i = 0; i < buffers.length; i++) {
            offset += buffers[i].byteLength;
            offset = (offset + 3) & ~3;
        }
        const view: any = { buffer: 0, byteOffset: offset, byteLength: arrayBuffer.byteLength };
        if (target) view.target = target;
        json.bufferViews.push(view);
        buffers.push(arrayBuffer);
        return json.bufferViews.length - 1;
    }

    const matCache: Record<string, number> = {};
    function materialIndex(color: [number, number, number]): number {
        const key = color.map((c) => c.toFixed(4)).join(",");
        if (matCache[key] !== undefined) return matCache[key];
        json.materials.push({
            pbrMetallicRoughness: {
                baseColorFactor: [color[0], color[1], color[2], 1.0],
                metallicFactor: 0.0,
                roughnessFactor: 0.9,
            },
        });
        matCache[key] = json.materials.length - 1;
        return matCache[key];
    }

    for (const o of objects) {
        // positions
        const posBuf = new Float32Array(o.positions).buffer;
        const posView = addBufferView(posBuf, 34962); // ARRAY_BUFFER
        const min = [Infinity, Infinity, Infinity];
        const max = [-Infinity, -Infinity, -Infinity];
        for (let j = 0; j < o.positions.length; j += 3) {
            for (let k = 0; k < 3; k++) {
                if (o.positions[j + k] < min[k]) min[k] = o.positions[j + k];
                if (o.positions[j + k] > max[k]) max[k] = o.positions[j + k];
            }
        }
        json.accessors.push({
            bufferView: posView,
            componentType: 5126, // FLOAT
            count: o.positions.length / 3,
            type: "VEC3",
            min, max,
        });
        const posAccIdx = json.accessors.length - 1;

        // indices
        const idxArray = new Uint32Array(o.indices as number[]);
        const idxView = addBufferView(idxArray.buffer, 34963); // ELEMENT_ARRAY_BUFFER
        json.accessors.push({
            bufferView: idxView,
            componentType: 5125, // UNSIGNED_INT
            count: idxArray.length,
            type: "SCALAR",
        });
        const idxAccIdx = json.accessors.length - 1;

        // mesh
        const prim: any = {
            attributes: { POSITION: posAccIdx },
            indices: idxAccIdx,
            material: materialIndex(o.color),
        };
        if (o.isLine) prim.mode = 1; // LINES
        json.meshes.push({ primitives: [prim] });

        json.nodes.push({ name: o.name, mesh: json.meshes.length - 1 });
        json.nodes[0].children.push(json.nodes.length - 1);
    }

    // concatenate buffers into one, 4-byte padded
    let total = 0;
    for (const b of buffers) {
        total += b.byteLength;
        total = (total + 3) & ~3;
    }
    const buffer = new Uint8Array(total);
    let offset = 0;
    for (const b of buffers) {
        buffer.set(new Uint8Array(b), offset);
        offset += b.byteLength;
        offset = (offset + 3) & ~3;
    }
    json.buffers.push({ byteLength: total });

    return { json, buffer: buffer.buffer };
}

function writeGLB(root: THREE.Object3D, filename: string) {
    const result = buildGLTF(root);
    const jsonBuf = new TextEncoder().encode(JSON.stringify(result.json));

    // GLB: header (12 bytes) + JSON chunk + BIN chunk, each 4-byte padded
    const jsonPad = (4 - (jsonBuf.byteLength % 4)) % 4;
    const binPad = (4 - (result.buffer.byteLength % 4)) % 4;
    const jsonLen = jsonBuf.byteLength + jsonPad;
    const binLen = result.buffer.byteLength + binPad;
    const total = 12 + 8 + jsonLen + 8 + binLen;

    const glb = new Uint8Array(total);
    const dv = new DataView(glb.buffer);

    dv.setUint32(0, 0x46546c67, true); // magic "glTF"
    dv.setUint32(4, 2, true);          // version
    dv.setUint32(8, total, true);      // total length

    dv.setUint32(12, jsonLen, true);
    dv.setUint32(16, 0x4e4f534a, true); // "JSON"
    glb.set(jsonBuf, 20);
    for (let i = 0; i < jsonPad; i++) glb[20 + jsonBuf.byteLength + i] = 0x20;

    const binStart = 20 + jsonLen;
    dv.setUint32(binStart, binLen, true);
    dv.setUint32(binStart + 4, 0x004e4942, true); // "BIN\0"
    glb.set(new Uint8Array(result.buffer), binStart + 8);

    downloadBlob(new Blob([glb], { type: "model/gltf-binary" }), filename);
}

// ---------------------------------------------------------------------------
// X3D writer
// ---------------------------------------------------------------------------

function writeX3D(root: THREE.Object3D, filename: string) {
    const objects = collectGeometry(root);
    const out: string[] = [];
    out.push('<?xml version="1.0" encoding="UTF-8"?>');
    out.push('<X3D profile="Interchange" version="3.3" xmlns:xsd="http://www.w3.org/2001/XMLSchema-instance">');
    out.push('  <head><meta name="generator" content="mcdisplay-export"/></head>');
    out.push("  <Scene>");

    for (const o of objects) {
        const [r, g, b] = o.color.map((c) => c.toFixed(4));
        const verts: string[] = [];
        for (let i = 0; i < o.positions.length; i += 3) {
            verts.push(`${o.positions[i].toFixed(6)} ${o.positions[i + 1].toFixed(6)} ${o.positions[i + 2].toFixed(6)}`);
        }
        const idx: string[] = [];
        for (let i = 0; i < o.indices.length; i += 3) {
            idx.push(`${o.indices[i]} ${o.indices[i + 1]} ${o.indices[i + 2]} -1`);
        }

        out.push("    <Transform>");
        out.push("      <Shape>");
        out.push(`        <Appearance><Material diffuseColor="${r} ${g} ${b}" emissiveColor="${r} ${g} ${b}"/></Appearance>`);
        if (o.isLine) {
            out.push(`        <IndexedLineSet coordIndex="${idx.join(" ")}">`);
        } else {
            out.push(`        <IndexedFaceSet solid="false" coordIndex="${idx.join(" ")}">`);
        }
        out.push(`          <Coordinate point="${verts.join(" ") }"/>`);
        out.push(o.isLine ? "        </IndexedLineSet>" : "        </IndexedFaceSet>");
        out.push("      </Shape>");
        out.push("    </Transform>");
    }

    out.push("  </Scene>");
    out.push("</X3D>");
    downloadText(out.join("\n"), filename, "model/x3d+xml");
}

// ---------------------------------------------------------------------------
// OBJ + MTL writer (per-object materials, world coordinates)
// ---------------------------------------------------------------------------

function writeOBJ(root: THREE.Object3D, basename: string) {
    const objects = collectGeometry(root);

    const objLines: string[] = [];
    const mtlLines: string[] = ["# materials generated by mcdisplay-export"];
    let vertexOffset = 1; // OBJ indices are 1-based
    const usedMtls: Record<string, boolean> = {};

    for (const o of objects) {
        const mtlName = "mat_" + o.name.replace(/[^A-Za-z0-9_]/g, "_");

        objLines.push("o " + o.name);
        objLines.push("g " + o.name);
        objLines.push("usemtl " + mtlName);
        if (!usedMtls[mtlName]) {
            usedMtls[mtlName] = true;
            mtlLines.push("newmtl " + mtlName);
            mtlLines.push("Ka 0 0 0");
            mtlLines.push(`Kd ${o.color[0].toFixed(4)} ${o.color[1].toFixed(4)} ${o.color[2].toFixed(4)}`);
            mtlLines.push("Ks 0 0 0");
            mtlLines.push("illum 1");
            mtlLines.push("");
        }

        for (let i = 0; i < o.positions.length; i += 3) {
            objLines.push(`v ${o.positions[i].toFixed(6)} ${o.positions[i + 1].toFixed(6)} ${o.positions[i + 2].toFixed(6)}`);
        }

        for (let i = 0; i < o.indices.length; i += 3) {
            const a = (o.indices as number[])[i] + vertexOffset;
            const b = (o.indices as number[])[i + 1] + vertexOffset;
            const c = (o.indices as number[])[i + 2] + vertexOffset;
            if (o.isLine) {
                objLines.push(`l ${a} ${b}`);
            } else {
                objLines.push(`f ${a} ${b} ${c}`);
            }
        }
        vertexOffset += o.positions.length / 3;
    }

    objLines.unshift("mtllib " + basename + ".mtl");
    downloadText(objLines.join("\n"), basename + ".obj");
    downloadText(mtlLines.join("\n"), basename + ".mtl");
}

// ---------------------------------------------------------------------------
// React component: floating export menu
// ---------------------------------------------------------------------------

import React, { useState } from "react";

interface ExportMenuProps {
    getRoot: () => THREE.Object3D | null;
}

export function ExportMenu({ getRoot }: ExportMenuProps) {
    const [format, setFormat] = useState<ExportFormat>("glb");
    const [includeRays, setIncludeRays] = useState(true);

    return (
        <div
        style={{
            position: "fixed",
            top: 10,
            right: 10,
            zIndex: 1000,
            background: "rgba(0,0,0,0.6)",
            padding: 8,
            borderRadius: 6,
            font: "12px sans-serif",
            color: "#fff",
            display: "flex",
            gap: 6,
            alignItems: "center",
        }}
        >
        <select
        value={format}
        onChange={(e) => setFormat(e.target.value as ExportFormat)}
        >
        <option value="glb">GLB (binary glTF)</option>
        <option value="gltf">glTF (JSON)</option>
        <option value="x3d">X3D</option>
        <option value="obj">OBJ + MTL</option>
        </select>
        <label style={{ color: "#fff" }}>
        <input
        type="checkbox"
        checked={includeRays}
        onChange={(e) => setIncludeRays(e.target.checked)}
        />{" "}
        include rays
        </label>
        <button onClick={() => exportModel(getRoot, format, includeRays)}>
        Export 3D model
        </button>
        </div>
    );
}

export default ExportMenu;
