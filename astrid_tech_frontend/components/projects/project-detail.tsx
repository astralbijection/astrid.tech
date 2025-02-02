import Link from "next/link";
import { join } from "path";
import { createContext, FC, useContext } from "react";
import path from "path";
import SEO from "../seo";
import {
  BsArrowLeft,
  BsCodeSlash,
  BsLink,
  BsQuestionCircle,
} from "react-icons/bs";
import { FaCalendar, FaEnvelope, FaGithub } from "react-icons/fa";
import { Container } from "reactstrap";
import { ProjectLink } from "../../lib/cache";
import { DateInterval } from "../util/date-displays";
import { getHSLString, getPersistentColor } from "../../lib/util";
import { Project } from "../../types/types";
import { CommentSection } from "../api/comments/CommentSection";
import { ContentDisplay } from "../content/ContentDisplay";
import ConstructionBanner from "components/util/construction";
import {
  InfoRow,
  Layout,
  LongformLayout,
  SidebarGroup,
  StatusGroup,
  TagsGroup,
} from "../layout";
import { StatusBadge } from "./project-card";
import style from "./project-detail.module.scss";
import { resolveAssetURL } from "../../lib/cache/assets";

type UsesProject = {
  project: Project<Date>;
};

function SourceCodeURLDisplay({ url }: { url: string }) {
  const info = new URL(url);
  if (info.hostname.endsWith("github.com")) {
    return (
      <a href={url}>
        <FaGithub title="GitHub" /> Github
      </a>
    );
  }
  if (info.protocol == "mailto:") {
    return (
      <a href={url}>
        <FaEnvelope /> {info.pathname}
      </a>
    );
  }
  return <a href={url}>{url}</a>;
}

const ProjectStatusGroup = () => {
  const { project } = useContext(ProjectContext);
  return (
    <StatusGroup>
      <InfoRow name="Dates" icon={<FaCalendar />}>
        <DateInterval
          formatStyle="d MMM yyyy"
          startDate={project.startDate}
          endDate={project.endDate}
        />
      </InfoRow>
      {project.url ? (
        <InfoRow name="URL" icon={<BsLink />}>
          <a href={project.url}>{project.url}</a>
        </InfoRow>
      ) : null}
      <InfoRow name="Source" icon={<BsCodeSlash />}>
        {project.source.map((url) => (
          <p key={url}>
            <SourceCodeURLDisplay url={url} />
          </p>
        ))}
      </InfoRow>
      <InfoRow name="Status" icon={<BsQuestionCircle />}>
        <StatusBadge status={project.status} />
      </InfoRow>
    </StatusGroup>
  );
};

/*
const BlogPostsGroup = () => {
  const { project } = useContext(ProjectContext);
  const blogPosts = (project.childProjectTag.childTag.tagged.filter(
    (item) => item.__typename == "BlogPost"
  ) as BlogPost[]).sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
  );

  const list = (
    <ul>
      {blogPosts.map((post) => (
        <li key={post.slug}>
          <Link to={post.slug}>
            {moment(post.date).format("MMM YYYY")} - {post.title}
          </Link>
        </li>
      ))}
    </ul>
  );
  return (
    <SidebarGroup>
      <h2>Associated Blog Posts</h2>
      {blogPosts.length == 0 ? <p>N/A</p> : list}
    </SidebarGroup>
  );
};
*/

type RelatedProjectsGroupProps = { similar: ProjectLink[] };

const RelatedProjectsGroup: FC<RelatedProjectsGroupProps> = ({ similar }) => {
  const list = (
    <ul>
      {similar.map(({ slug, title }) => (
        <li key={slug}>
          <Link href={slug}>{title}</Link>
        </li>
      ))}
    </ul>
  );

  return (
    <SidebarGroup>
      <h2>Similar Projects</h2>
      {similar.length == 0 ? <p>N/A</p> : list}
    </SidebarGroup>
  );
};

type ProjectContextData = {
  project: Project;
};

const ProjectContext = createContext<ProjectContextData>(
  {} as ProjectContextData
);

export type ProjectDetailProps = UsesProject & {
  similar: ProjectLink[];
};

const ConstructionDisclaimer: FC = () => {
  return (
    <>
      <section className="text-center">
        <h4>
          <strong>NOTE:</strong> This section is under construction!
        </h4>
        <ConstructionBanner />
        <p>
          <em>
            The contents of this page are incomplete and subject to change.
            Check back later for a more complete version!
          </em>
        </p>
      </section>
      <hr />
    </>
  );
};

const ProjectDetailPage: FC<ProjectDetailProps> = ({ project, similar }) => {
  const slug = join("projects", project.slug);
  const url = join(process.env.publicRoot!, slug);
  const thumbnail = project.thumbnail
    ? path.join(
        process.env.publicRoot!!,
        resolveAssetURL(project.assetRoot, project.thumbnail)
      )
    : undefined;

  const descriptionRaw = project.description ?? "A project made by Astrid Yu";
  const underConstruction = project.tags.includes("under-construction");

  return (
    <ProjectContext.Provider value={{ project }}>
      <SEO
        canonicalUrl={url}
        title={project.title!}
        description={descriptionRaw}
        image={thumbnail}
      />
      <Layout currentLocation="projects">
        <LongformLayout
          title={project.title}
          description={project.description}
          thumbnail={thumbnail}
          descriptionRaw={descriptionRaw}
          headingColor={getHSLString(getPersistentColor(slug))}
          above={
            <Link href="/projects/" passHref>
              <a className={style.backToProjects} rel="directory">
                <BsArrowLeft /> Back to Projects
              </a>
            </Link>
          }
          url={url}
          sidebar={
            <>
              <ProjectStatusGroup />
              <TagsGroup tags={project.tags} />
              {/* TODO <BlogPostsGroup /> */}
              <RelatedProjectsGroup similar={similar} />
            </>
          }
        >
          {underConstruction ? <ConstructionDisclaimer /> : null}
          <ContentDisplay>{project.content}</ContentDisplay>
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

export default ProjectDetailPage;
