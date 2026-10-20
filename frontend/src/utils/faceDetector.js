import { FaceDetector, FilesetResolver } from '@mediapipe/tasks-vision'

let detectorPromise

export function getFaceDetector() {
  if (!detectorPromise) {
    detectorPromise = FilesetResolver.forVisionTasks('/mediapipe-wasm')
      .then(vision => FaceDetector.createFromOptions(vision, {
        baseOptions: {
          modelAssetPath: '/models/blaze_face_short_range.tflite',
          delegate: 'GPU',
        },
        runningMode: 'VIDEO',
        minDetectionConfidence: 0.5,
        minSuppressionThreshold: 0.3,
      }))
  }
  return detectorPromise
}

export async function detectFaces(detector, canvas) {
  const result = detector.detectForVideo(canvas, performance.now())
  return result.detections || []
}
