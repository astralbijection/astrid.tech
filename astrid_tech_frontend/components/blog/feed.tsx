import { format } from "date-fns";
import Link from "next/link";
import { FC } from "react";
import { Row } from "reactstrap";
import { blogSlugToString, getBlogSlug } from "../../lib/util";
import style from "../../styles/blog.module.scss";
import { BlogPostMeta } from "../../types/types";
import { TagList } from "../tags/tag";

type PostProps = {
  post: BlogPostMeta<Date>;
};

export const PostBrief: FC<PostProps> = ({ post }) => {
  const dateString = format(post.date, "d MMMM yyyy");
  const url = blogSlugToString(getBlogSlug(post));
  console.log(post);

  return (
    <Link href={url}>
      <article className={style.brief}>
        <Row>
          <div className="col-12 col-sm-8 col-md-7">
            <a href={url}>
              {post.title ? <h3>{post.title}</h3> : null}
              {post.description ? <p>{post.description}</p> : null}
              <p className="text-muted">{post.excerpt}</p>
            </a>
          </div>
          <div className="col col-sm-4 col-md-5">
            <p className={`text-muted ${style.date}`}>{dateString}</p>
            <p>
              <TagList tags={post.tags} link limit={5} />
            </p>
          </div>
        </Row>
      </article>
    </Link>
  );
};

export type BlogFeedProps = {
  posts: BlogPostMeta<Date>[];
};

export const BlogFeed: FC<BlogFeedProps> = ({ posts }) => {
  return (
    <div>
      {posts.map((post) => (
        <PostBrief key={post.slug} post={post} />
      ))}
      <p className="text-center text-muted">(End of posts)</p>
    </div>
  );
};
