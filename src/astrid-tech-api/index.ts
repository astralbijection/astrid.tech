import axios, { AxiosInstance, AxiosResponse } from "axios"

export type CommentForm = {
  author_name?: string
  author_email: string
  author_website?: string
  content_md: string
  slug: string
}

export type CommentData = {
  id: string
  author_name?: string
  author_email: string
  author_website?: string
  content_md: string
  content_html: string
  children: CommentData[]
  slug: string
}

export class AstridTechAPI {
  private axios: AxiosInstance

  constructor(private readonly root: string) {
    this.axios = axios.create({ baseURL: root })
  }

  async createComment(
    comment: CommentForm,
    replyTo?: number
  ): Promise<AxiosResponse<CommentData>> {
    if (replyTo === undefined) {
      return await this.axios.post("/api/comments/", comment)
    }

    return await this.axios.post(`/api/comments/${replyTo}/`, comment)
  }

  async getComments(slug: string): Promise<AxiosResponse<CommentData[]>> {
    return await this.axios.get("/api/comments/", { params: { slug } })
  }
}
