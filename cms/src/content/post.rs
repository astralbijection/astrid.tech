use std::convert::TryFrom;
use std::io::Write;

use chrono::{Datelike, DateTime, FixedOffset};
use gray_matter::engine::yaml::YAML;
use gray_matter::entity::ParsedEntityStruct;
use gray_matter::matter::Matter;
use serde::{Deserialize, Serialize};
use url::Url;
use uuid::Uuid;
use vfs::{VfsFileType, VfsPath};

use crate::content::content::{Content, ContentType, find_unique_with_name, FindFilenameError, ReadPostContentError, UnsupportedContentType};
use crate::content::post_registry::DateSlug;
use crate::web::micropub::{Entry, Micropub};
use std::str::FromStr;

#[derive(Debug)]
pub enum PostError {
    Filesystem(vfs::VfsError),
    IO(std::io::Error),
    YAML(serde_yaml::Error),
    Serde(serde_json::error::Error),
    AmbiguousIndex(FindFilenameError),
    AmbiguousContent(FindFilenameError),
    UnsupportedContentType(UnsupportedContentType),
    ContentTypeDoesNotSupportFrontmatter(ContentType),
    NotADirectory(VfsPath),
    ReadPost(ReadPostContentError),
}

impl From<vfs::VfsError> for PostError {
    fn from(e: vfs::VfsError) -> Self {
        PostError::Filesystem(e)
    }
}

impl From<serde_yaml::Error> for PostError {
    fn from(e: serde_yaml::Error) -> Self {
        PostError::YAML(e)
    }
}

impl From<serde_json::Error> for PostError {
    fn from(e: serde_json::Error) -> Self {
        PostError::Serde(e)
    }
}

impl From<std::io::Error> for PostError {
    fn from(e: std::io::Error) -> Self {
        PostError::IO(e)
    }
}

impl From<UnsupportedContentType> for PostError {
    fn from(e: UnsupportedContentType) -> Self {
        PostError::UnsupportedContentType(e)
    }
}

impl From<ReadPostContentError> for PostError {
    fn from(e: ReadPostContentError) -> Self {
        PostError::ReadPost(e)
    }
}

#[derive(Serialize, Deserialize, Debug, Eq, PartialEq, Clone)]
pub struct MediaEntry {
    image: String,
    caption: String,
}

#[derive(Serialize, Deserialize, Debug, Eq, PartialEq, Clone)]
pub struct RecipeStep {
    text: String
}

#[derive(Serialize, Deserialize, Debug, Eq, PartialEq, Clone)]
#[serde(tag = "status", rename_all = "camelCase")]
pub enum Syndication {
    Scheduled {
        url: Url,
    },
    #[serde(rename_all = "camelCase")]
    Completed {
        url: Url,
        completed_on: DateTime<FixedOffset>,
    },
}

#[derive(Serialize, Deserialize, Debug, Eq, PartialEq, Clone)]
#[serde(tag = "type")]
pub enum HType {
    #[serde(rename = "entry")]
    Entry,
    #[serde(rename = "recipe")]
    Recipe {
        //duration: Option<Duration>,
        ingredients: Vec<String>,
        instructions: Vec<RecipeStep>,
    },
}

#[derive(Serialize, Deserialize, Debug, Eq, PartialEq, Clone)]
#[serde(rename_all = "camelCase")]
pub struct Meta {
    #[serde(flatten)]
    pub h_type: HType,

    pub title: Option<String>,
    pub description: Option<String>,
    pub short_name: Option<String>,
    pub uuid: Uuid,

    pub date: DateTime<FixedOffset>,
    pub published_date: Option<DateTime<FixedOffset>>,
    pub updated_date: Option<DateTime<FixedOffset>>,
    #[serde(default)]
    pub ordinal: u32,

    pub reply_to: Option<Url>,
    pub repost_of: Option<Url>,
    #[serde(default)]
    pub tags: Vec<String>,
    #[serde(default)]
    pub syndications: Vec<Syndication>,
    #[serde(default)]
    pub media: Vec<MediaEntry>,
}

impl Meta {
    pub fn get_slug(&self) -> DateSlug {
        let utc = self.date.naive_utc();
        DateSlug {
            year: utc.year(),
            month: utc.month() as u8,
            day: utc.day() as u8,
            ordinal: self.ordinal,
        }
    }
}

#[derive(Eq, PartialEq, Clone, Debug)]
pub struct Post {
    pub meta: Meta,
    pub content: Content,
}

impl Post {
    pub fn write_to(&self, path: &mut VfsPath) -> Result<(), PostError> {
        let extension = self.content.content_type.to_ext();

        if self.content.content_type.supports_frontmatter() {
            // If our content type supports having frontmatter, create a single file.
            let mut filename = "index.".to_string();
            filename.push_str(extension);

            let mut file = path.join(filename.as_str())?.create_file()?;
            let meta_yaml = serde_yaml::to_string(&self.meta)?;
            file.write(meta_yaml.as_bytes())?;
            file.write("\n---\n".as_ref())?;
            file.write(self.content.content.as_bytes())?;

            return Ok(());
        }

        {
            let mut filename = "content.".to_string();
            filename.push_str(extension);
            let meta_file = path.join(filename.as_str())?.create_file()?;
            serde_yaml::to_writer(meta_file, &self.meta)?;
        }
        {
            let mut content_file = path.join("index.yaml")?.create_file()?;
            content_file.write(self.content.content.as_bytes())?;
        }

        Ok(())
    }

    pub fn get_slug(&self) -> DateSlug {
        self.meta.get_slug()
    }

    pub fn from_micropub_entry(uuid: Uuid, date: DateTime<FixedOffset>, ordinal: u32, entry: Entry) -> Post {
        let short_name = "".to_string();

        let meta = Meta {
            title: entry.name,
            description: entry.summary,
            short_name: Some(short_name),
            uuid,
            date,
            published_date: entry.published,
            updated_date: entry.updated,
            ordinal,
            reply_to: entry.in_reply_to,
            repost_of: entry.repost_of,
            tags: entry.category,
            syndications: entry.mp_syndicate_to.iter()
                .map(|url| {
                    Syndication::Scheduled { url: url.clone() }
                })
                .collect(),
            h_type: HType::Entry,
            media: vec![],
        };

        let content = Content {
            content_type: ContentType::Markdown,
            content: entry.content.unwrap_or_default(),
        };

        Post { meta, content }
    }

    pub fn from_micropub(uuid: Uuid, date: DateTime<FixedOffset>, ordinal: u32, mp: Micropub) -> Post {
        match mp {
            Micropub::Entry(e) => Self::from_micropub_entry(uuid, date, ordinal, e),
            Micropub::Event(_) => { todo!() }
            Micropub::Cite(_) => { todo!() }
        }
    }
}

impl TryFrom<VfsPath> for Post {
    type Error = PostError;

    /// Creates a post from a post directory.
    fn try_from(path: VfsPath) -> Result<Self, Self::Error> {
        if path.metadata()?.file_type != VfsFileType::Directory {
            Err(PostError::NotADirectory(path.clone()))?;
        }

        let index_name = find_unique_with_name("index", &path).map_err(PostError::AmbiguousIndex)?;
        let index_path = path.join(index_name.as_str())?;

        let ext = index_path.extension().unwrap();
        if ext == "yaml" || ext == "yml" {
            let file = index_path.open_file()?;
            let meta: Meta = serde_yaml::from_reader(file)?;

            let content_filename = find_unique_with_name("content", &path).map_err(PostError::AmbiguousContent)?;
            let content_path = path.join(content_filename.as_str())?;
            let content = Content::try_from(content_path)?;

            return Ok(Post { meta, content });
        }

        let content_type = ContentType::from_ext(ext.as_str())?;
        if !content_type.supports_frontmatter() {
            Err(PostError::ContentTypeDoesNotSupportFrontmatter(content_type))
        } else {
            let contents = index_path.read_to_string()?;
            let matter = Matter::<YAML>::new();
            let parsed: ParsedEntityStruct<Meta> = matter.matter_struct(contents);

            let content = Content::new(content_type, parsed.content);
            Ok(Post { meta: parsed.data, content })
        }
    }
}

#[cfg(test)]
pub mod test {
    use std::convert::TryFrom;
    use std::io::Write;

    use vfs::{MemoryFS, VfsPath};

    use crate::content::content::ContentType;
    use crate::content::post::Post;

    const TXT_ARTICLE_YAML: &str = r#"
date: 2021-06-12 10:51:30 +08:00
title: Example post with text

type: entry
shortName: foo-bar
uuid: 2fdb77e7-a019-4e51-9ba4-cd6b2eedd60e
ordinal: 0
tags:
  - rust
  - python
  - csharp
"#;
    const TXT_CONTENTS: &str = r#"
foo bar spam
"#;

    fn setup_working_separate_content_post() -> VfsPath {
        let root = VfsPath::new(MemoryFS::new());
        {
            let mut file = root.join("index.yaml").unwrap().create_file().unwrap();
            file.write(TXT_ARTICLE_YAML.as_ref()).unwrap();
        }
        {
            let mut file = root.join("content.txt").unwrap().create_file().unwrap();
            file.write(TXT_CONTENTS.as_ref()).unwrap();
        }
        root
    }

    fn setup_working_combined_post() -> VfsPath {
        let root = VfsPath::new(MemoryFS::new());

        let mut file = root.join("index.md").unwrap().create_file().unwrap();
        file.write("---\n".as_ref()).unwrap();
        file.write(TXT_ARTICLE_YAML.as_ref()).unwrap();
        file.write("\n---\n".as_ref()).unwrap();
        file.write(TXT_CONTENTS.as_ref()).unwrap();

        root
    }

    pub fn get_working_separate_content_post() -> Post {
        Post::try_from(setup_working_separate_content_post()).unwrap()
    }

    pub fn get_working_combined_post() -> Post {
        Post::try_from(setup_working_combined_post()).unwrap()
    }

    #[test]
    fn reads_separate_content() {
        let path = setup_working_separate_content_post();

        let post = Post::try_from(path).unwrap();

        assert_eq!(post.content.content_type, ContentType::Text);
        assert_eq!(post.content.content, TXT_CONTENTS);
    }

    #[test]
    fn reads_joined_content() {
        let path = setup_working_combined_post();

        let post = Post::try_from(path).unwrap();

        assert_eq!(post.content.content_type, ContentType::Markdown);
        assert_eq!(post.content.content.trim(), "foo bar spam");
    }

    #[test]
    fn writes_separate_content_correctly() {
        let mut new_fs = VfsPath::new(MemoryFS::new());
        let expected = get_working_separate_content_post();

        expected.write_to(&mut new_fs);

        let actual = Post::try_from(new_fs).unwrap();
        assert_eq!(actual, expected);
    }

    #[test]
    fn writes_combined_content_correctly() {
        let mut new_fs = VfsPath::new(MemoryFS::new());
        let expected = get_working_combined_post();

        expected.write_to(&mut new_fs);

        let actual = Post::try_from(new_fs).unwrap();
        assert_eq!(actual, expected);
    }
}
