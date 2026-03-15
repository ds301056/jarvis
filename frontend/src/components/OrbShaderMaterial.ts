// Simplex 3D noise + vertex displacement shader for the Jarvis orb

export const vertexShader = /* glsl */ `
  uniform float uTime;
  uniform float uAmplitude;
  uniform float uSpeed;
  uniform float uNoiseScale;
  uniform float uSpikeAmount;  // 0.0 = off (current look), 1.0 = full dramatic spikes

  varying vec3 vNormal;
  varying vec3 vPosition;

  //
  // Simplex 3D noise (Ashima Arts)
  //
  vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
  vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
  vec4 permute(vec4 x) { return mod289(((x * 34.0) + 10.0) * x); }
  vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }

  float snoise(vec3 v) {
    const vec2 C = vec2(1.0/6.0, 1.0/3.0);
    const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);

    vec3 i = floor(v + dot(v, C.yyy));
    vec3 x0 = v - i + dot(i, C.xxx);

    vec3 g = step(x0.yzx, x0.xyz);
    vec3 l = 1.0 - g;
    vec3 i1 = min(g.xyz, l.zxy);
    vec3 i2 = max(g.xyz, l.zxy);

    vec3 x1 = x0 - i1 + C.xxx;
    vec3 x2 = x0 - i2 + C.yyy;
    vec3 x3 = x0 - D.yyy;

    i = mod289(i);
    vec4 p = permute(permute(permute(
      i.z + vec4(0.0, i1.z, i2.z, 1.0))
      + i.y + vec4(0.0, i1.y, i2.y, 1.0))
      + i.x + vec4(0.0, i1.x, i2.x, 1.0));

    float n_ = 0.142857142857;
    vec3 ns = n_ * D.wyz - D.xzx;

    vec4 j = p - 49.0 * floor(p * ns.z * ns.z);

    vec4 x_ = floor(j * ns.z);
    vec4 y_ = floor(j - 7.0 * x_);

    vec4 x = x_ * ns.x + ns.yyyy;
    vec4 y = y_ * ns.x + ns.yyyy;
    vec4 h = 1.0 - abs(x) - abs(y);

    vec4 b0 = vec4(x.xy, y.xy);
    vec4 b1 = vec4(x.zw, y.zw);

    vec4 s0 = floor(b0) * 2.0 + 1.0;
    vec4 s1 = floor(b1) * 2.0 + 1.0;
    vec4 sh = -step(h, vec4(0.0));

    vec4 a0 = b0.xzyw + s0.xzyw * sh.xxyy;
    vec4 a1 = b1.xzyw + s1.xzyw * sh.zzww;

    vec3 p0 = vec3(a0.xy, h.x);
    vec3 p1 = vec3(a0.zw, h.y);
    vec3 p2 = vec3(a1.xy, h.z);
    vec3 p3 = vec3(a1.zw, h.w);

    vec4 norm = taylorInvSqrt(vec4(dot(p0,p0), dot(p1,p1), dot(p2,p2), dot(p3,p3)));
    p0 *= norm.x;
    p1 *= norm.y;
    p2 *= norm.z;
    p3 *= norm.w;

    vec4 m = max(0.6 - vec4(dot(x0,x0), dot(x1,x1), dot(x2,x2), dot(x3,x3)), 0.0);
    m = m * m;
    return 42.0 * dot(m*m, vec4(dot(p0,x0), dot(p1,x1), dot(p2,x2), dot(p3,x3)));
  }

  void main() {
    float t = uTime * uSpeed;
    vec3 pos = position;

    // Multi-octave noise for organic feel
    float noise1 = snoise(pos * uNoiseScale + t * 0.5);
    float noise2 = snoise(pos * uNoiseScale * 2.0 + t * 0.8) * 0.5;
    float displacement = (noise1 + noise2) * uAmplitude;

    // Audio-reactive spikes: high-frequency noise that shoots outward
    // Only active when uSpikeAmount > 0 (controlled by setting)
    if (uSpikeAmount > 0.0) {
      // Sharp spikes using high-frequency noise, powered by audio amplitude
      float spike1 = snoise(pos * 4.0 + t * 2.0);
      float spike2 = snoise(pos * 7.0 + t * 3.5) * 0.6;
      float spikeMask = max(spike1, 0.0);  // only outward spikes
      spikeMask = pow(spikeMask, 1.5);     // sharpen the peaks
      float spikeDisp = (spikeMask + max(spike2, 0.0) * 0.4) * uAmplitude * uSpikeAmount * 2.5;
      displacement += spikeDisp;
    }

    pos += normal * displacement;

    vNormal = normalize(normalMatrix * normal);
    vPosition = (modelViewMatrix * vec4(pos, 1.0)).xyz;

    gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
  }
`

export const fragmentShader = /* glsl */ `
  uniform vec3 uColor;

  varying vec3 vNormal;
  varying vec3 vPosition;

  void main() {
    // Fresnel effect — glow at edges
    vec3 viewDir = normalize(-vPosition);
    float fresnel = 1.0 - max(dot(viewDir, vNormal), 0.0);
    fresnel = pow(fresnel, 2.5);

    // Base color with fresnel brightening
    vec3 color = uColor * (0.4 + fresnel * 1.5);

    // Subtle ambient light from above
    float topLight = dot(vNormal, vec3(0.0, 1.0, 0.0)) * 0.15 + 0.85;
    color *= topLight;

    // Add glow at edges
    color += uColor * fresnel * 0.6;

    gl_FragColor = vec4(color, 0.92 + fresnel * 0.08);
  }
`
