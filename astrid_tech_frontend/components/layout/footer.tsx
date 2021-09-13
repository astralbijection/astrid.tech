import Link from "next/link";
import { FC, PropsWithChildren, ReactNode } from "react";
import { Col, Container, Row } from "reactstrap";
import style from "./footer.module.scss";
import packageJson from "../../package.json";

export const Tea = () => {
  return (
    <span title="tea" aria-label="tea" role="img">
      ☕
    </span>
  );
};

export const Witch = () => {
  return (
    <span title="witchcraft" aria-label="witchcraft" role="img">
      🧙‍
    </span>
  );
};

const ContentLicense = () => (
  <p>
    <a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/">
      <img
        alt="Creative Commons License"
        src="/cc-by-nc-sa-4.0.png"
        width={88}
        height={31}
      />
    </a>
    <br />
    <span
      {...{ "xmlns:dct": "http://purl.org/dc/terms/" }}
      property="dct:title"
    >
      The page content of astrid.tech
    </span>{" "}
    by{" "}
    <a
      {...{ "xmlns:cc": "http://creativecommons.org/ns#" }}
      href={process.env.publicRoot}
      property="cc:attributionName"
      rel="cc:attributionURL"
    >
      Astrid Yu
    </a>{" "}
    is licensed under a{" "}
    <a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/">
      Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International
      License
    </a>
    .
  </p>
);

const AGPL: FC = () => {
  return (
    <>
      <a rel="license" href="https://www.gnu.org/licenses/agpl-3.0.en.html">
        <img
          alt="GNU Affero General Public License"
          width={100}
          height={40}
          src="/agpl.png"
        />
      </a>
      <p>
        <a href="https://github.com/astralbijection/astrid.tech">
          The source code of astrid.tech
        </a>{" "}
        is licensed under the{" "}
        <a href="https://www.gnu.org/licenses/agpl-3.0.en.html">AGPL License</a>
        .{" "}
      </p>
    </>
  );
};

/**
 * Links for an IndieWebRing. For more info, see https://xn--sr8hvo.ws/dashboard
 * @returns links :)
 */
const IndieWebRing: FC = () => {
  return (
    <WebRing
      prev="https://xn--sr8hvo.ws/%F0%9F%9A%AF%F0%9F%90%9E%F0%9F%8C%8A/previous"
      next="https://xn--sr8hvo.ws/%F0%9F%9A%AF%F0%9F%90%9E%F0%9F%8C%8A/next"
    >
      <span title="An IndieWeb Webring">🕸💍</span>
    </WebRing>
  );
};

const XXIIVVWebring: FC = () => {
  // TODO update when I get someone after me
  return (
    <WebRing
      prev="https://webring.xxiivv.com/#yhnck"
      next="https://webring.xxiivv.com/#xxiivv"
    >
      <img
        src="https://webring.xxiivv.com/icon.white.svg"
        style={{ height: "1em" }}
        title="XXIIVV's Webring"
      />
    </WebRing>
  );
};

type WebRingProps = PropsWithChildren<{
  next: string;
  prev: string;
}>;

const WebRing: FC<WebRingProps> = ({ next, prev, children }) => {
  return (
    <p style={{ fontSize: 20, marginBottom: 0 }}>
      <a href={prev} rel="prev">
        &larr;
      </a>{" "}
      {children}{" "}
      <a href={next} rel="next">
        &rarr;
      </a>
    </p>
  );
};

type SiteLinkProps = {
  href: string;
  children: ReactNode;
};

const SiteLink: FC<SiteLinkProps> = ({ href, children }) => (
  <Col xs={6} sm={4}>
    <Link href={href}>{children}</Link>
  </Col>
);

type MiniAboutProps = { version: string };

const MiniAbout: FC<MiniAboutProps> = ({ version }) => {
  return (
    <p className="h-card">
      <a href="https://astrid.tech" className="u-url" rel="me">
        astrid.tech
      </a>{" "}
      v{version} was created by <span className="p-name">Astrid Yu</span> with a
      generous helping of <Tea /> and <Witch />. Read the{" "}
      <Link href="/projects/astrid-tech">self-referential project page</Link> or
      see the code yourself on{" "}
      <a href="https://github.com/astralbijection/astrid.tech">GitHub</a>.
    </p>
  );
};

const FooterSection = () => {
  const version = packageJson.version;

  return (
    <footer className={style.footer}>
      <Container className="text-light">
        <Row>
          <Col tag="nav" className="text-center" sm="3">
            <h6>Webrings</h6>
            <IndieWebRing />
            <XXIIVVWebring />
          </Col>

          <Col sm="9">
            <Row tag="nav">
              <SiteLink href="/privacy">Privacy Policy</SiteLink>
              <SiteLink href="/licenses">Open Source Licenses</SiteLink>
              <SiteLink href="/about">About/Contact</SiteLink>
            </Row>

            <Row className="small">
              <MiniAbout version={version} />
            </Row>

            <Row className="small">
              <Row>
                <Col className="text-center">
                  <AGPL />
                </Col>
                <Col className="text-center">
                  <ContentLicense />
                </Col>
              </Row>
            </Row>
          </Col>
        </Row>
      </Container>
    </footer>
  );
};

export default FooterSection;
