export interface SteganalysisResult {
  filename: string
  format: string  // 'png', 'bmp', 'jpg', 'webp', 'wav', 'flac'
  filesize_bytes: number
  image_dimensions: [number, number]
  risk_score: number
  risk_label: 'clean' | 'uncertain' | 'suspicious' | 'likely_embedded'

  chi_squared: {
    r: number
    g: number
    b: number
    threshold: number
  }

  rs_analysis: {
    r: number[]
    s: number[]
    rm: number[]
    sm: number[]
    estimated_rate: number
  }

  sample_pair: {
    estimated_rate: number
    confidence: number
  }

  lsb_entropy: {
    grid: number[][]
    hot_zones: string[]
  }
}
