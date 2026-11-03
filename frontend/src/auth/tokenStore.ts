// Penyimpan token di memori. Field privat (#): token tidak ikut ter-enumerasi, tidak tampil saat objek
// dicetak, dan tidak pernah ditulis ke penyimpanan peramban (Keputusan 3).
export class TokenStore {
  #token: string | null = null

  get(): string | null {
    return this.#token
  }

  set(token: string): void {
    this.#token = token
  }

  clear(): void {
    this.#token = null
  }
}
