import React, { Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, useGLTF, Preload, Html } from '@react-three/drei';

// A loader component to show while the model is loading
function Loader() {
  return (
    <Html center>
      <div style={{ color: 'white' }}>Loading 3D model...</div>
    </Html>
  );
}

// The component that loads and displays the GLB model
function Model({ url }) {
  const { scene } = useGLTF(url);
  // The model might not have a scale set, so we can apply a default one.
  // We can also adjust position and rotation if needed.
  return <primitive object={scene} scale={1} position={[0, 0, 0]} />;
}

export default function Viewer({ url }) {
  return (
    <Canvas
      camera={{ position: [0, 2, 5], fov: 75 }}
      style={{ background: '#1a1a1a', width: '100%', height: '100%' }}
    >
      <Suspense fallback={<Loader />}>
        {/* Basic lighting for the scene */}
        <ambientLight intensity={1.5} />
        <directionalLight position={[10, 10, 5]} intensity={1} />
        <directionalLight position={[-10, -10, -5]} intensity={0.5} />

        {/* The model to be displayed, only if URL is present */}
        {url && <Model url={url} />}

        {/* Controls for user interaction */}
        <OrbitControls />

        {/* Helper to preload assets */}
        <Preload all />
      </Suspense>
    </Canvas>
  );
}
