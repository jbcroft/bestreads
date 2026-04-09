export type BookStatus = "want_to_read" | "reading" | "finished" | "dnf";

export interface Tag {
  id: string;
  name: string;
}

export interface Book {
  id: string;
  title: string;
  author: string;
  isbn: string | null;
  page_count: number | null;
  description: string | null;
  cover_url: string | null;
  status: BookStatus;
  rating: number | null;
  notes: string | null;
  date_added: string;
  started_at: string | null;
  finished_at: string | null;
  tags: Tag[];
}

export interface UserPublic {
  id: string;
  username: string;
  email: string;
  avatar_url: string | null;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface StatsResponse {
  total_books: number;
  by_status: Record<BookStatus, number>;
  finished_this_year: number;
  avg_rating: number | null;
  top_tags: { name: string; count: number }[];
  finished_by_month: { month: string; count: number }[];
}

export interface SearchResponse {
  want_to_read: Book[];
  reading: Book[];
  finished: Book[];
  dnf: Book[];
}

export interface LookupResult {
  title: string;
  author: string;
  isbn: string | null;
  page_count: number | null;
  description: string | null;
  cover_image_path: string | null;
  cover_url: string | null;
}

export interface LookupSearchItem {
  title: string;
  author: string;
  year: number | null;
  isbn: string | null;
  cover_url: string | null;
}

export interface RecommendationItem {
  title: string;
  author: string;
  reason: string;
}

export interface RecommendationsResponse {
  available: boolean;
  message: string | null;
  recommendations: RecommendationItem[];
  generated_at: string | null;
}
