import { format } from "date-fns";
import { join } from "path";
import { createContext, FC, useContext } from "react";
import { FaCalendar } from "react-icons/fa";
import { Container } from "reactstrap";
import {
  blogSlugToString,
  getBlogSlug,
  getHSLString,
  getPersistentColor,
  truncateKeepWords,
} from "../../lib/util";
import { BlogPost } from "../../types/types";
import { CommentSection } from "../api/comments/CommentSection";
import { ContentDisplay } from "../content";
import Layout from "../layout/layout";
import {
  InfoRow,
  LongformLayout,
  StatusGroup,
  TagsGroup,
} from "../layout/longform-layout";
import SEO from "../seo";
import striptags from "striptags";

type PostContextData = {
  post: BlogPost<Date>;
};

const ProjectContext = createContext<PostContextData>({} as PostContextData);

const PostStatusGroup: FC = () => {
  const { post } = useContext(ProjectContext);
  const date = format(post.date, "d MMM yyyy");
  return (
    <StatusGroup>
      <InfoRow name="Date" icon={<FaCalendar />}>
        {date}
      </InfoRow>
      {/* TODO add comment count */}
    </StatusGroup>
  );
};

export type BlogPostPageProps = { post: BlogPost<Date> };

export const BlogPostPage: FC<BlogPostPageProps> = ({ post }) => {
  const slug = blogSlugToString(getBlogSlug(post));
  const url = join(process.env.publicRoot!, slug);

  const metaTitle = post.title
    ? post.title
    : truncateKeepWords(striptags(post.content), 50) + "...";

  return (
    <ProjectContext.Provider value={{ post }}>
      <SEO title={metaTitle} description={post.description} />
      <Layout currentLocation="blog">
        <LongformLayout
          title={post.title}
          url={url}
          description={post.description}
          descriptionRaw={post.description}
          headingColor={getHSLString(getPersistentColor(slug))}
          sidebar={
            <>
              <PostStatusGroup />
              <TagsGroup tags={post.tags} />
            </>
          }
          above={null}
        >
          <article className="longform">
            <ContentDisplay>{post.content}</ContentDisplay>
          </article>
        </LongformLayout>
        <Container>
          <section id="comments">
            <h2>Comments</h2>
            <CommentSection slug={slug} />
          </section>
        </Container>
      </Layout>
    </ProjectContext.Provider>
  );
};

export default BlogPostPage;
