import Hls from 'hls.js';

export function initHls(
  videoEl: HTMLVideoElement,
  manifestUrl: string,
): Hls | null {
  if (Hls.isSupported()) {
    const hls = new Hls();
    hls.loadSource(manifestUrl);
    hls.attachMedia(videoEl);
    return hls;
  }
  // Native HLS — Safari
  if (videoEl.canPlayType('application/vnd.apple.mpegurl')) {
    videoEl.src = manifestUrl;
    return null;
  }
  throw new Error('HLS is not supported in this browser');
}
